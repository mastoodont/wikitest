WikiTest
This repository contains automated tests for the Wikipedia page about Playwright (software), built using Playwright, NUnit, and Allure for reporting. The tests validate specific functionalities and content on the Wikipedia page, ensuring consistency and correctness of the UI and API data.
Project Overview
The project includes a C# test suite (WikiTests 100 (1).cs) that performs the following tasks:

Compare Unique Words: Compares the unique word count in the "Debugging features" section of the Playwright Wikipedia page between the UI (rendered content) and the Wikipedia API.
Validate Technology Links: Verifies that all technology names in the "Microsoft development tools" section are clickable hyperlinks.
Dark Mode Switch: Switches the Wikipedia page to Dark Mode and verifies that the dark theme is applied correctly.

Prerequisites
To run the tests, ensure you have the following installed:

.NET SDK (version 6.0 or higher)
Playwright for .NET
NUnit (for test execution)
Allure CLI (for generating test reports)
A modern web browser (Chromium, Firefox, or WebKit) for Playwright

Setup

Clone the repository:
git clone https://github.com/mastoodont/wikitest.git
cd wikitest


Install Playwright dependencies:Run the following command to install browser binaries for Playwright:
pwsh bin/Debug/netX.0/playwright.ps1 install

(Replace netX.0 with your .NET version, e.g., net6.0.)

Restore project dependencies:Ensure all NuGet packages are installed:
dotnet restore


Build the project:
dotnet build



Running Tests
To execute the tests, run:
dotnet test

This will run all tests in the WikiTests class, targeting the Playwright Wikipedia page (https://en.wikipedia.org/wiki/Playwright_(software)).
Test Details

CompareDebuggingWords: Fetches the "Debugging features" section text via UI and Wikipedia API, normalizes the text, and compares the count of unique words.
ValidateTechLinks: Ensures all technology names in the "Microsoft development tools" section are valid hyperlinks.
SwitchAndVerifyDarkMode: Switches the page to Dark Mode and checks if the skin-theme-clientpref-night class is applied to the body.

Generating Allure Reports
To generate and view Allure reports:

Run tests with Allure results:dotnet test -- NUnit.Allure


Generate the report:allure generate allure-results --clean


Open the report:allure open



Project Structure

WikiTests 100 (1).cs:
WikiPage: Page Object Model for interacting with the Wikipedia page.
TextNormalizer: Utility for normalizing text and counting unique words.
WikiTests: Test class containing the three test cases.
API response models for Wikipedia API parsing.



Contributing
Contributions are welcome! Feel free to:

Submit bug reports or feature requests via Issues.
Fork the repository, make changes, and submit a pull request.

License
This project is licensed under the MIT License. See the LICENSE file for details.
