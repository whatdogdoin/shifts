Auto add shifts to google calendar from In-N-Out emails, runs 24/7 but only checks for new emails every 12 hours

I AM NOT GOOD AT PYTHON.  RUN AT YOUR OWN RISK.  I AM PROVIDING DOCUMENTATION FOR HOPEFUL EASE OF USE

There are a couple of things that are needed in order to run this script because I am not going to bother making it something not run locally:
1. Python and pip.  This is a python project that is run in the command line, I recommend using a Raspberry Pi or some other single board computer to run this script at low power.
   
2. Google developer account for access to Gmail and Google Calendar APIs, I didn't know which ones to enable so I just selected all of them, feel free to experiment on your own time as I am probably never going to mess with this
   Everything in the screenshots below is in OAuth consent screen
   ![image](https://github.com/user-attachments/assets/f9d09ca7-9474-40d1-944f-d113b951d9ad)
   ![image](https://github.com/user-attachments/assets/f00d41f6-4ade-45a1-8a07-cad9f8147129)
   ![image](https://github.com/user-attachments/assets/1395e52c-c25f-44f9-811d-6e48291eaa92)
   ![image](https://github.com/user-attachments/assets/a1882e7e-98ac-4084-8b3d-2f1d40f4481d)

   Go to credentials and create credentials, with authorized redirect URIs as http://localhost:57053/.  localhost means it is running only on your computer, this is not sending information anywhere else
   Save and download the .json file and rename it to credentials.json
3. Run these commands in Powershell to install neccessary dependancies
   pip install --upgrade google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2
   pip install beautifulsoup4

4. Put script.py and credentials.json in their own folder, shouldn't really matter where.
5. Open Command Prompt or Powershell and run either "script.py" or if that does not work "python script.py"
