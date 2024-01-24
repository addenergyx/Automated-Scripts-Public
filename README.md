# Automated-Scripts-Public
A public version of my automated scripts repo

Utilises web scraping (Selenium, beautifulSoup), AWS resources (Lambda, dynamodb), hidden site APIs, and public APIs to automate repetitive tasks.

- **[Debt Management Automation](paydown_service/README.md)**: Implemented a script to automate the payment process for Klarna transactions, which required reverse engineering Klarna's API and seamless integration with Google Calendar for payment reminders.
- **[Gift Card Tracking](giftcards/README.md)**: Created a system to track the balance and expiry of ASDA gift cards, involving automated email forwarding to S3, triggering a Lambda function that updates Google Photos for easy access to gift card information.
- **[Crypto Cashback Tracking](plutus_tracker/README.md)**: Designed a tool to track the status of Plutus crypto cashback rewards, adding calendar events for reward release dates and identifying rejected transactions using hidden API endpoints.
- **[Unidays Renewal](unidays_renewal/README.md)**: Auto renewing student membership.

