from dataclasses import dataclass
from application.queue_manager import QueueManager

@dataclass
class GoogleConfig:
    headless: bool
    total_emails: int
    total_steps: int
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
        return "https://accounts.google.com/SignUp?continue=https://myaccount.google.com%3Futm_source%3Daccount-marketing-page%26utm_medium%3Dcreate-account-button"

@dataclass
class EmailGoogleVericatorText:
    name: str
    day_birthday: str
    month_birthday: str
    year_birthday: str
    gender: str

# Configurações do Google
google_config = GoogleConfig(
    headless=True,
    total_emails=1,
    total_steps=3,
    selector_step_one="#firstName",
    selector_button_step_one="#collectNameNext > div > button > span",
    selector_step_two_day="#day",
    selector_step_two_month="#month",
    selector_step_two_year="#year",
    selector_step_two_gender="#gender",
    selector_button_step_two="#birthdaygenderNext > div > button > span",
    selector_sugester_email="#selectionc3",
    selector_input_email="#yDmH0d > c-wiz > div > div.UXFQgc > div > div > div > form > span > section > div > div > div.BvCjxe > div.AFTWye > div > div.aCsJod.oJeWuf > div > div.Xb9hP > input",
    selector_button_next_email="#next > div > button > span",
    selector_message_email="#yDmH0d > c-wiz > div > div.UXFQgc > div > div > div > form > span > section > div > div > div.BvCjxe > div.AFTWye > div > div.LXRPh > div.dEOOab.RxsGPe > div > span"
)

# Texto para preenchimento
google_email_text = EmailGoogleVericatorText(
    name="Alexandre",
    day_birthday="10",
    month_birthday="O",
    year_birthday="1990",
    gender="H"
)

# Filas para o Google
google_queues = QueueManager().create_queues_for_service("google")