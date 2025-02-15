#driver_manager.py
from queue import Empty
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import threading
import time
from typing import Optional, Any
import logging
from requests.exceptions import ConnectionError, ReadTimeout
from selenium.common.exceptions import WebDriverException
import backoff

class EnhancedDriverManager:
    def __init__(
        self,
        verifier_class: type,
        config: Any,
        email_text: Any,
        queues: Any,
        idle_timeout: int = 300,
        max_retries: int = 3,
        retry_delay: int = 5
    ):
        self.verifier_class = verifier_class
        self.config = config
        self.email_text = email_text
        self.queues = queues
        self.driver: Optional[webdriver.Chrome] = None
        self.verifier = None
        self.last_activity: Optional[float] = None
        self.idle_timeout = idle_timeout
        self.is_running = False
        self.lock = threading.Lock()
        self.monitor_thread: Optional[threading.Thread] = None
        self.verification_thread: Optional[threading.Thread] = None
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger('DriverManager')
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    @backoff.on_exception(
        backoff.expo,
        (ConnectionError, ReadTimeout, WebDriverException),
        max_tries=3,
        jitter=None
    )
    def _create_driver(self) -> webdriver.Chrome:
        """Creates and configures the Chrome WebDriver with exponential backoff retry"""
        options = Options()
        if self.config.headless:
            options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        # Add connection timeout settings
        options.add_argument('--network-timeout=30000')
        options.add_argument('--proxy-server="direct://"')
        options.add_argument('--proxy-bypass-list=*')

        service = Service(ChromeDriverManager().install())
        service.start()  # Explicitly start the service
        
        return webdriver.Chrome(service=service, options=options)

    def start_driver(self) -> bool:
        """Starts the Selenium driver with enhanced error handling"""
        self.logger.info("Starting start_driver method")
        with self.lock:
            if self.driver:
                self.logger.info("Driver already running")
                return False
            for attempt in range(self.max_retries):
                try:
                    self.logger.info(f"Attempting to start driver (attempt {attempt + 1}/{self.max_retries})")
                    self.driver = self._create_driver()
                    # Initialize verifier
                    self.verifier = self.verifier_class(
                        config=self.config,
                        email_text=self.email_text,
                        queues=self.queues
                    )
                    self.verifier.driver = self.driver
                    # Start processing
                    self.is_running = True
                    self.start_queue_processing()
                    self.start_monitoring()
                    self.update_activity()
                    self.logger.info("Driver successfully started")
                    return True
                except Exception as e:
                    self.logger.error(f"Error starting driver (attempt {attempt + 1}): {str(e)}")
                    if self.driver:
                        try:
                            self.driver.quit()
                        except:
                            pass
                        self.driver = None
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
                    else:
                        self.logger.error("Max retries reached, unable to start driver")
                        return False
            return False
        self.logger.info("Exiting start_driver method")

    def shutdown_driver(self) -> bool:
        """Gracefully shuts down the driver and all associated processes"""
        with self.lock:
            if not self.driver:
                return False

            self.logger.info("Initiating driver shutdown")
            try:
                self.is_running = False

                # Espera as threads terminarem, mas evita chamar join na própria thread ativa
                if self.verification_thread and self.verification_thread.is_alive():
                    self.verification_thread.join(timeout=5)
                
                if self.monitor_thread and self.monitor_thread.is_alive():
                    if threading.current_thread() != self.monitor_thread:
                        self.monitor_thread.join(timeout=5)
                    else:
                        self.logger.warning("Monitor thread tentou dar join em si mesma, ignorando.")

                # Quit driver
                try:
                    self.driver.quit()
                except Exception as e:
                    self.logger.error(f"Error while quitting driver: {e}")
                finally:
                    self.driver = None
                    self.verifier = None
                    self.last_activity = None

                self.logger.info("Driver shutdown completed successfully")
                return True

            except Exception as e:
                self.logger.error(f"Error during driver shutdown: {e}")
                return False


    def start_queue_processing(self) -> None:
        """Inicia a thread de processamento da fila"""
        self.verification_thread = threading.Thread(
            target=self._process_queue,
            daemon=True
        )
        self.verification_thread.start()

    def start_monitoring(self) -> None:
        """Inicia o monitoramento de inatividade"""
        self.monitor_thread = threading.Thread(
            target=self._monitor_idle_time,
            daemon=True
        )
        self.monitor_thread.start()

    def _process_queue(self) -> None:
        """Processa a fila de verificação de emails"""
        while self.is_running:
            try:
                # Tenta obter um item da fila com timeout
                queue_item = self.queues.email_queue.get(timeout=1)
                
                try:
                    # Realiza a verificação
                    verification_result = self.verifier.verify_email(queue_item.data)
                    
                    # Atualiza o resultado
                    result = {
                        "email": queue_item.data,
                        "available": verification_result,
                        "verified_at": datetime.utcnow().isoformat()
                    }
                    self.queues.update_verification(queue_item.id, result)
                    
                    self.update_activity()
                    
                except Exception as e:
                    # Em caso de erro, atualiza o status da verificação
                    error_result = {
                        "email": queue_item.data,
                        "error": str(e),
                        "verified_at": datetime.utcnow().isoformat()
                    }
                    self.queues.update_verification(queue_item.id, error_result)
                    
            except Empty:
                # Timeout da fila, continua o loop
                continue
            except Exception as e:
                print(f"Erro no processamento da fila: {e}")
                time.sleep(1)  # Evita loop muito rápido em caso de erro

    def _monitor_idle_time(self) -> None:
        """Monitora o tempo de inatividade do driver"""
        while self.is_running:
            try:
                if self.last_activity and time.time() - self.last_activity > self.idle_timeout:
                    print("Driver inativo por muito tempo, desligando...")
                    self.shutdown_driver()
                time.sleep(10)  # Verifica a cada 10 segundos
            except Exception as e:
                print(f"Erro no monitoramento de inatividade: {e}")

    def update_activity(self) -> None:
        """Atualiza o timestamp da última atividade"""
        self.last_activity = time.time()