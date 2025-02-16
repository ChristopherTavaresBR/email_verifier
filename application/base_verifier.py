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
    """
    Abstract base class for email verification. Provides common functionality for
    interacting with a web driver, processing a verification queue, and logging.

    Attributes:
        config (Any): Configuration settings for the verifier.
        email_text (Any): Text or data related to email verification.
        queues (VerificationQueues): Queues for managing email verification tasks.
        timeout (int): Default timeout for web driver operations (default: 5 seconds).
        driver (Optional[webdriver.Chrome]): The Selenium WebDriver instance.
        logger (logging.Logger): Logger for tracking events and errors.
        verification_thread (Optional[threading.Thread]): Thread for processing the verification queue.
        is_running (bool): Indicates whether the verification process is running.
    """
    def __init__(self, config, email_text, queues: VerificationQueues, timeout=5):
        self.config = config
        self.email_text = email_text
        self.queues = queues
        self.timeout = timeout
        self.driver = None 
        self.logger = self._setup_logging()
        self.verification_thread = None
        self.is_running = True
    
    def start_verification_process(self):
        """Starts the verification process in a separate thread."""
        self.verification_thread = threading.Thread(target=self._process_verification_queue)
        self.verification_thread.daemon = True
        self.verification_thread.start()
    
    def _process_verification_queue(self):
        """Processes emails from the queue continuously."""
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
        """
        Sets up and configures the logger for the class.

        Returns:
            logging.Logger: Configured logger instance.
        """
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(self.__class__.__name__)
        
    def setup_driver(self):
        """
        Configures and initializes the Selenium WebDriver.

        Returns:
            webdriver.Chrome: Configured WebDriver instance.
        """
        options = Options()
        if self.config.headless:
            options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        service = ChromeService(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)
    
    def _process_verification_queue(self):
        """Processes the verification queue."""
        while self.is_running:
            try:
                # Get email from queue
                email = self.queues.email_queue.get(timeout=1)  # Timeout to allow checking of is_running
                
                # Verify email
                result = self.verify_email(email)
                
                # Put result in result queue
                self.queues.result_queue.put({email: result})
                
            except queue.Empty:
                continue  # Continue loop if no emails in the queue
            except Exception as e:
                self.logger.error(f"Error processing email: {e}")
                self.queues.result_queue.put({"error": str(e)})
    
    def verify_element_exists(self, selector, timeout=None):
        """
        Verifies if an element exists on the page.

        Args:
            selector (str): CSS selector for the element.
            timeout (Optional[int]): Timeout for the operation (default: self.timeout).

        Returns:
            bool: True if the element exists, False otherwise.
        """
        try:
            WebDriverWait(self.driver, self.timeout if timeout is None else timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            self.logger.info(f"Element '{selector}' found...")
            return True
        except TimeoutException:
            self.logger.warning(f"Timeout while trying to find element '{selector}'...")
            return False

    def inputer_text(self, selector, text, step, clear=False):
        """
        Inputs text into a web element.

        Args:
            selector (str): CSS selector for the element.
            text (str): Text to input.
            step (str): Step identifier for logging.
            clear (bool): Whether to clear the field before inputting text (default: False).
        """
        try:
            elemnt = WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            if clear:
                elemnt.clear()  # Clear the field
            elemnt.send_keys(text)
            self.logger.info(f"Text '{text}' added to field '{selector} #step {step}'...")
        except TimeoutException:
            self.logger.warning(f"Timeout while trying to add text '{text}' to field '{selector} #step {step}'...")

    def click_button(self, selector, step, exception=TimeoutException):
        """
        Clicks a button on the page.

        Args:
            selector (str): CSS selector for the button.
            step (str): Step identifier for logging.
            exception (Exception): Exception to catch (default: TimeoutException).
        """
        try:
            WebDriverWait(self.driver, self.timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
            ).click()
            self.logger.info(f"Button '{selector}' clicked #step {step}...")
        except exception:
            self.logger.warning(f"Button '{selector}' not found #step {step}...")
    
    @abstractmethod
    def verify_email(self, email: str) -> bool:
        """
        Abstract method for email verification. Must be implemented by subclasses.

        Args:
            email (str): The email address to verify.

        Returns:
            bool: True if the email is valid, False otherwise.
        """
        pass
    
    def stop(self):
        """Stops the verification process."""
        self.is_running = False
        if self.verification_thread:
            self.verification_thread.join()