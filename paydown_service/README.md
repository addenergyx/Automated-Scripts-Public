# Paydown Service for Klarna Transactions

### Deprecation Notice
This script is now deprecated as Klarna has updated its service to allow customers to pay for all transactions in one step.

### Intent

Klarna, a popular payment service provider, previously required customers to individually pay off each transaction, making the process tedious for those with multiple transactions. 
This script was developed to automate these payments, saving users time and effort.

Without the ability to pay off an entire statement at once, Klarna users, including myself, found it cumbersome to complete up to 8 clicks per transaction, particularly when dealing with numerous transactions.

To address this inefficiency, the Paydown Service script automates the payment process. 
It navigates and interacts with Klarna's website to complete payments on behalf of the user.

### Design

The script utilizes Selenium for web automation. 
Due to the involvement of card payments and OTP (One-Time Password) codes, running this script on a serverless platform like AWS Lambda wasn't feasible. 
Instead, it leverages the OS ecosystem's synergy between iPhone and Mac. 
OTPs sent to the iPhone are accessible via a local iMessage SQLite database on the Mac, which the script uses to authenticate payments.