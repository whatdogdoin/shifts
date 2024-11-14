Fixed it





Auto add shifts to google calendar from In-N-Out emails, runs 24/7 but only checks for new emails every 12 hours

I AM NOT GOOD AT PYTHON.  RUN AT YOUR OWN RISK.  I AM PROVIDING DOCUMENTATION FOR HOPEFUL EASE OF USE

There are a couple of things that are needed in order to run this script because I am not going to bother making it something not run locally:
1. You need a credentials.json file that has access to Google API for this to work.  The .exe is compiled from the code in script.py but since I am unverified, the download will likely be blocked and may also be blocked by Windows Defender.  This .exe is safe, whether or not you trust it is up to you
   
2. Google developer account for access to Gmail and Google Calendar APIs, I didn't know which ones to enable so I just selected all of them, feel free to experiment on your own time as I am probably never going to mess with this
   Everything in the screenshots below is in OAuth consent screen<br />
   ![image](https://github.com/user-attachments/assets/f9d09ca7-9474-40d1-944f-d113b951d9ad)<br />
   ![image](https://github.com/user-attachments/assets/f00d41f6-4ade-45a1-8a07-cad9f8147129)<br />
   ![image](https://github.com/user-attachments/assets/1395e52c-c25f-44f9-811d-6e48291eaa92)<br />
   ![image](https://github.com/user-attachments/assets/a1882e7e-98ac-4084-8b3d-2f1d40f4481d)<br />

   Go to credentials and create credentials, with authorized redirect URIs as http://localhost:57053/.  localhost means it is running only on your computer, this is not sending information anywhere else
   Save and download the .json file and rename it to credentials.json

3. Put script.exe and credentials.json in their own folder, shouldn't really matter where.
4. run script.exe and watch your calendars populate with your shifts if you received emails within the past 2 days.
