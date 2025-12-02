import requests
import time 
import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

class StravaAPI:
    def __init__(self, client_id, client_secret, code=None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.code = code
        self.read_all_url = f"https://www.strava.com/oauth/authorize?client_id={client_id}&redirect_uri=http://localhost/exchange_token&response_type=code&scope=read,activity:read_all&approval_prompt=force"
        self.activies_endpoint = "https://www.strava.com/api/v3/athlete/activities"
        self.activate_api_url = "https://www.strava.com/oauth/token"
    
    def connect(self):
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": self.code,
            "grant_type": "authorization_code"
        }

        tokens = requests.post(url=self.activate_api_url, data=payload).json() 
        refresh_token = tokens["refresh_token"]

        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }

        refreshed = requests.post(self.activies_endpoint, data=payload).json()
        access_token = tokens["access_token"]
        self.headers = {"Authorization": f"Bearer {access_token}"}

    def make_request_nondetailed(self, page, per_page):
        r = requests.get(self.activies_endpoint, headers=self.headers, params={"page":page, "per_page": per_page})
        activities = r.json()
        return activities
    
    def make_request_detailed(self, activity_id):
        activities_with_id = f"{self.activies_endpoint}/{activity_id}"
        r = requests.get(activities_with_id, headers=self.headers)
        specific_activity = r.json()
        
        setattr(self, f'activity_{activity_id}', specific_activity) # this may need tweaking based on setattr rules

    def pull_activity_data(self, num_activities='all'):
        activities_list = []
        page = 1
        
        if num_activities == 'all':
            for _ in range(12):
                response = self.make_request_nondetailed(page=page, per_page=100)
                activities_list.extend(response)
                page+=1
        else:
            if num_activities >= 100:
                pages = num_activities // 100
                remainder = num_activities % 100
                for _ in range(pages-1):
                    response = self.make_request_nondetailed(page=page, per_page=100)
                    activities_list.extend(response)
                    page+=1
                
                response = self.make_request_nondetailed(page=pages, per_page=remainder)
                activities_list.extend(response)
            else:
                page = 1
                response = self.make_request_nondetailed(page=1, per_page=num_activities)
                activities_list.extend(response)

        self.activies_list = activities_list # maybe change to return list itself
    

class StravaML(StravaAPI):
    def __init__(self, client_id, client_secret, code=None):
        super().__init__(client_id, client_secret, code)