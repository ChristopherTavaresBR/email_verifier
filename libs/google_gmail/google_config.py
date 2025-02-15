# google_config.py
from dataclasses import dataclass
from application.config_base import BaseConfig


URL_CREATE_ACCOUNT = "https://accounts.google.com/SignUp?continue=https://myaccount.google.com%3Futm_source%3Daccount-marketing-page%26utm_medium%3Dcreate-account-button"


@dataclass
class GoogleConfig(BaseConfig):
    selector_step_one: str
    selector_button_step_one: str
    selector_step_two_day: str
    selector_step_two_month: str
    selector_step_two_year: str
    selector_step_two_gender: str
    selector_button_step_two: str
    selector_sugester_email: str
    selector_input_email: str
    selector_button_next_email: str
    selector_message_email: str
    
    def get_verification_url(self) -> str:
        return URL_CREATE_ACCOUNT
    

@dataclass
class EmailGoogleVericatorText:
    name: str
    day_birthday: str
    month_birthday: str
    year_birthday: str
    gender: str
