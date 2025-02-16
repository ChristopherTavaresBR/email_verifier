import logging
import threading
import time
import backoff
from queue import Empty
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from typing import Optional, Any
from requests.exceptions import ConnectionError, ReadTimeout


class EnhancedDriverManager:
    """
    Manages the lifecycle of a Selenium WebDriver with enhanced error handling,
    retries, and inactivity monitoring.

    Attributes:
        verifier_class (type): The class responsible for email verification.
        config (Any): Configuration settings for the driver.
        email_text (Any): Text or data related to email verification.
        queues (Any): Queues for managing email verification tasks.
        idle_timeout (int): Maximum allowed idle time before shutting down the driver (default: 300 seconds).
        max_retries (int): Maximum number of retries for starting the driver (default: 3).
        retry_delay (int): Delay between retries in seconds (default: 5).
        driver (Optional[webdriver.Chrome]): The Selenium WebDriver instance.
        verifier (Optional[Any]): The email verifier instance.
        last_activity (Optional[float]): Timestamp of the last activity.
        is_running (bool): Indicates whether the driver is running.
        lock (threading.Lock): Lock for thread-safe operations.
        monitor_thread (Optional[threading.Thread]): Thread for monitoring inactivity.
        verification_thread (Optional[threading.Thread]): Thread for processing the verification queue.
        logger (logging.Logger): Logger for tracking events and errors.
    """
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
        """
        Sets up and configures the logger for the class.

        Returns:
            logging.Logger: Configured logger instance.
        """
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
        """
        Creates and configures the Chrome WebDriver with exponential retry.

        Returns:
            webdriver.Chrome: Configured WebDriver instance.
        """
        options = Options()
        if self.config.headless:
            options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--network-timeout=30000')
        options.add_argument('--proxy-server="direct://"')
        options.add_argument('--proxy-bypass-list=*')

        service = Service(ChromeDriverManager().install())
        service.start()  # Explicitly starts the service
        return webdriver.Chrome(service=service, options=options)

    def start_driver(self) -> bool:
        """
        Starts the Selenium driver with enhanced error handling and retries.

        Returns:
            bool: True if the driver started successfully, False otherwise.
        """
        self.logger.info("Starting the driver...")
        with self.lock:
            if self.driver:
                self.logger.info("Driver is already running.")
                return False

            for attempt in range(self.max_retries):
                try:
                    self.logger.info(f"Attempt {attempt + 1}/{self.max_retries} to start the driver...")
                    self.driver = self._create_driver()
                    self.verifier = self.verifier_class(
                        config=self.config,
                        email_text=self.email_text,
                        queues=self.queues
                    )
                    self.verifier.driver = self.driver
                    self.is_running = True
                    self.start_queue_processing()
                    self.start_monitoring()
                    self.update_activity()
                    self.logger.info("Driver started successfully.")
                    return True
                except Exception as e:
                    self.logger.error(f"Error starting the driver (attempt {attempt + 1}): {e}")
                    if self.driver:
                        try:
                            self.driver.quit()
                        except:
                            pass
                        self.driver = None
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
                    else:
                        self.logger.error("Max retries reached. Unable to start the driver.")
                        return False
            return False

    def shutdown_driver(self) -> bool:
        """
        Shuts down the driver and all associated processes.

        Returns:
            bool: True if the driver was shut down successfully, False otherwise.
        """
        with self.lock:
            if not self.driver:
                return False

            self.logger.info("Initiating driver shutdown...")
            try:
                self.is_running = False

                if self.verification_thread and self.verification_thread.is_alive():
                    self.verification_thread.join(timeout=5)
                
                if self.monitor_thread and self.monitor_thread.is_alive():
                    if threading.current_thread() != self.monitor_thread:
                        self.monitor_thread.join(timeout=5)
                    else:
                        self.logger.warning("Monitor thread attempted to join itself. Ignoring.")

                try:
                    self.driver.quit()
                except Exception as e:
                    self.logger.error(f"Error shutting down the driver: {e}")
                finally:
                    self.driver = None
                    self.verifier = None
                    self.last_activity = None

                self.logger.info("Driver shut down successfully.")
                return True
            except Exception as e:
                self.logger.error(f"Error during driver shutdown: {e}")
                return False

    def start_queue_processing(self) -> None:
        """Starts the queue processing thread."""
        self.verification_thread = threading.Thread(
            target=self._process_queue,
            daemon=True
        )
        self.verification_thread.start()

    def start_monitoring(self) -> None:
        """Starts the inactivity monitoring thread."""
        self.monitor_thread = threading.Thread(
            target=self._monitor_idle_time,
            daemon=True
        )
        self.monitor_thread.start()

    def _process_queue(self) -> None:
        """Processes the email verification queue."""
        while self.is_running:
            try:
                email = self.queues.email_queue.get(timeout=1)
                result = self.verifier.verify_email(email)
                self.queues.result_queue.put({email: result})
                self.update_activity()
            except Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error processing the queue: {e}")

    def _monitor_idle_time(self) -> None:
        """Monitors the driver's idle time and shuts it down if inactive for too long."""
        while self.is_running:
            try:
                if self.last_activity and time.time() - self.last_activity > self.idle_timeout:
                    self.logger.info("Driver inactive for too long. Shutting down...")
                    self.shutdown_driver()
                time.sleep(10)
            except Exception as e:
                self.logger.error(f"Error monitoring inactivity: {e}")

    def update_activity(self) -> None:
        """Updates the timestamp of the last activity."""
        self.last_activity = time.time()