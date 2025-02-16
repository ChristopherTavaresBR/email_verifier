from application.base_verifier import BaseEmailVerifier


class GoogleEmailVerifier(BaseEmailVerifier):
    """
    A specialized email verifier for Google accounts. It extends the `BaseEmailVerifier`
    class to implement the specific steps required to verify if an email address is available
    for registration on Google.

    Attributes:
        Inherits all attributes from `BaseEmailVerifier`.
    """

    def verify_email(self, email: str) -> bool:
        """
        Verifies if a given email address is available for registration on Google.

        Args:
            email (str): The email address to verify.

        Returns:
            bool: True if the email is available, False otherwise.
        """
        try:
            if not self.driver:
                self.logger.error("Driver not initialized")
                return False

            # Step 1: Access the account creation page
            self.driver.get(self.config.get_verification_url())
            self.logger.info(f"Accessing URL: {self.config.get_verification_url()}")

            # Step 2: Fill in the name
            self.inputer_text(self.config.selector_step_one, self.email_text.name, '1')
            self.logger.info("Name added #step 1...")
            self.click_button(self.config.selector_button_step_one, '1')

            # Step 3: Fill in birthdate and gender
            self.logger.info(f"Step 2/{self.config.total_steps}...")
            self.inputer_text(self.config.selector_step_two_day, self.email_text.day_birthday, '2')
            self.inputer_text(self.config.selector_step_two_month, self.email_text.month_birthday, '2')
            self.inputer_text(self.config.selector_step_two_year, self.email_text.year_birthday, '2')
            self.inputer_text(self.config.selector_step_two_gender, self.email_text.gender, '2')
            self.logger.info("Gender and birthdate added...")
            self.click_button(self.config.selector_button_step_two, '2')

            # Step 4: Select suggested email
            self.logger.info("Waiting for email suggestion selector...")
            self.click_button(self.config.selector_sugester_email, '3')

            # Step 5: Verify the email
            self.logger.info(f"Verifying email: {email}@gmail.com...")
            self.inputer_text(self.config.selector_input_email, email, 'Verify', True)
            self.click_button(self.config.selector_button_next_email, "verify")

            # Step 6: Check for error message (email availability)
            is_available = self.verify_element_exists(self.config.selector_message_email, 2)
            
            if not is_available:
                self.driver.back()  # Go back to try another email if needed
            
            return is_available

        except Exception as e:
            self.logger.error(f"Error during email verification: {e}")
            return False