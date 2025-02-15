from abc import ABC, abstractmethod
import queue
import threading
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import logging

from application.queue_manager import VerificationQueues

class BaseEmailVerifier(ABC):
    def __init__(self, config, email_text, queues: VerificationQueues, timeout=5):
        self.config = config
        self.email_text = email_text
        self.queues = queues
        self.timeout = timeout
        self.driver = None  # Não inicializa o driver aqui
        self.logger = self._setup_logging()
        self.verification_thread = None
        self.is_running = True
    
    def start_verification_process(self):
        """Start the verification process in a separate thread."""
        self.verification_thread = threading.Thread(target=self._process_verification_queue)
        self.verification_thread.daemon = True
        self.verification_thread.start()
    
    def _process_verification_queue(self):
        """Process emails from the queue continuously."""
        while True:
            try:
                # Get email from queue
                email = self.queues.email_queue.get()
                
                # Verify email
                result = self.verify_email(email)
                
                # Put result in result queue
                self.queues.result_queue.put({email: result})
                
            except Exception as e:
                self.logger.error(f"Error processing email: {e}")
                # Put error result in queue
                self.queues.result_queue.put({"error": str(e)})

    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(self.__class__.__name__)
        
    def setup_driver(self):
        options = Options()
        if self.config.headless:
            options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        service = ChromeService(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)
    
    def _process_verification_queue(self):
        """Processa a fila de verificação"""
        while self.is_running:
            try:
                # Get email from queue
                email = self.queues.email_queue.get(timeout=1)  # timeout para permitir verificação de is_running
                
                # Verify email
                result = self.verify_email(email)
                
                # Put result in result queue
                self.queues.result_queue.put({email: result})
                
            except queue.Empty:
                continue  # Continua o loop se não houver emails na fila
            except Exception as e:
                self.logger.error(f"Error processing email: {e}")
                self.queues.result_queue.put({"error": str(e)})
    
    def verify_element_exists(self, selector, timeout=None):
        try:
            WebDriverWait(self.driver, self.timeout if timeout is None else timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            self.logger.info(f"Elemento '{selector}' encontrado...")
            return True
        except TimeoutException:
            self.logger.warning(f"Timeout ao tentar encontrar o elemento '{selector}'...")
            return False

    def inputer_text(self, selector, text, step, clear=False):
        try:
            elemnt = WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            if clear:
                elemnt.clear()  # Limpa o campo
            elemnt.send_keys(text)
            self.logger.info(f"Texto '{text}' adicionado ao campo '{selector} #step {step}'...")
        except TimeoutException:
            self.logger.warning(f"Timeout ao tentar adicionar o texto '{text}' ao campo '{selector} #step {step}'...")

    def click_button(self, selector, step, exception=TimeoutException):
        try:
            WebDriverWait(self.driver, self.timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
            ).click()
            self.logger.info(f"Botão '{selector}' clicado #step {step}...")
        except exception:
            self.logger.warning(f"Botão '{selector}' não encontrado #step {step}...")
    
    #@abstractmethod
    #def verify_email(self, email: str) -> bool:
    #    pass

    @abstractmethod
    def verify_email(self, email: str) -> bool:
        """Implementação específica da verificação de email"""
        pass
    
    def stop(self):
        """Para o processamento da fila"""
        self.is_running = False
        if self.verification_thread:
            self.verification_thread.join()