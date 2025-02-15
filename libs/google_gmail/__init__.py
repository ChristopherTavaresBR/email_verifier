from application.queue_manager import QueueManager
from google_gmail.google_config import EmailGoogleVericatorText, GoogleConfig

queue_manager = QueueManager()

google_queues = queue_manager.create_queues_for_service('google')

google_config = GoogleConfig(
    headless=False,
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

google_email_text = EmailGoogleVericatorText(
    name="Alexandre",
    day_birthday="10",
    month_birthday="O",
    year_birthday="1990",
    gender="H"
)
