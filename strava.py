import requests
import time 
import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

class StravaAPI:
    def __init__(self, client_id, client_secret, code=None, file_name='activity_data.csv', context_file_name='formatted_sts'):
        self.client_id = client_id
        self.client_secret = client_secret
        self.code = code
        self.read_all_url = f"https://www.strava.com/oauth/authorize?client_id={client_id}&redirect_uri=http://localhost/exchange_token&response_type=code&scope=read,activity:read_all&approval_prompt=force"
        self.activies_endpoint = "https://www.strava.com/api/v3/activities"
        self.activate_api_url = "https://www.strava.com/oauth/token"
        self.file_name = file_name 
        self.context_file_name = context_file_name
    
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

    # combine detailed with this?
    def pull_activity_data(self, num_activities='all'):
        activities_list = []
        page = 1
        
        if num_activities == 'all':
            for _ in range(12):
                response = self.make_request_nondetailed(page=page, per_page=100)
                activities_list.extend(response)
                page+=1
        else:
            # can probably concatenate this logic 
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

        self.activities_list = activities_list # maybe change to return list itself

    def pull_song(self, string):
        try:
            if ':' in string:
                split = "Song OTD:"
            else: 
                split = "Song OTD"
            res = string.split(split)[1].split('by')[0].strip()
            return res
        except:
            return 'NA'
        
    def pull_artist(self, string):
        try:
            if ':' in string:
                split = "Song OTD:"
            else: 
                split = "Song OTD"
            res = string.split(split)[1].split('by')[1].strip()
            return res
        except:
            return 'NA'

    def pull_artist_and_song(self, string):
        try:
            if ':' in string:
                split = "Song OTD:"
            else: 
                split = "Song OTD"
            res = string.split(split)[1]
            return res
        except:
            return 'NA'    

    def format_pace(self, x):
        if np.isnan(x):
            return 'NA'
        else:
            second_frac = x - int(x)
            seconds = int((60) * second_frac)
            if seconds < 10:
                seconds = f"0{seconds}"
            return f"{int(x)}:{seconds}"
        
    def extract_lat(self, x):
        try:
            return x[0]
        except:
            return 'NA'

    def extract_long(self, x):
        try:
            return x[1]
        except:
            return 'NA'

    # split this out to do feature engineering separately
    def refresh_dataset(self, max_lookback=25):
        existing_data = pd.read_csv(self.file_name)
        
        self.pull_activity_data(num_activities=max_lookback)
        
        all_keys = set().union(*[dic.keys() for dic in self.activities_list])

        to_add = pd.DataFrame([{key: dic.get(key, None) for key in all_keys} for dic in self.activities_list])
        new_ids = np.setdiff1d(to_add['id'].tolist(), existing_data['id'].tolist())
        to_add = to_add[to_add['id'].isin(new_ids)]
        to_add['date_str'] = to_add['start_date'].apply(lambda x: pd.Timestamp(x).date())
        to_add['time_mins'] = to_add['elapsed_time'].apply(lambda x: x / 60)
        to_add['distance_miles'] = to_add['distance'] * 0.000621371
        to_add['pace'] = np.where(to_add['type'] == 'Run', to_add['time_mins'] / to_add['distance_miles'], np.nan)
        to_add['pace_formatted'] = to_add['pace'].apply(self.format_pace)
        to_add['speed_mph'] = to_add['distance_miles'] / (to_add['time_mins'] / 60)
        to_add = to_add[(to_add['pace'] <= 12) & (to_add['type'] == 'Run')].sort_values('date_str', ascending=True)

        for col in ['start_latlng', 'end_latlng']:
            start_end = col.split('_')[0]
            to_add[f'{start_end}_lat'] = to_add[col].apply(self.extract_lat)
            to_add[f'{start_end}_long'] = to_add[col].apply(self. extract_long)

        #outdoor_runs = to_add[(to_add['start_lat'] != 'NA') & (to_add['end_lat'] != 'NA')]

        descriptions = []
        for id in new_ids:
            self.make_request_detailed(activity_id=id)
            response = getattr(self, f"activity_{id}")
            description = response['description']

            descriptions.append(description)
            time.sleep(15)


        descriptions = pd.DataFrame({
            "id" : new_ids,
            "description" : descriptions
        })

        to_add = pd.merge(left=to_add, right=descriptions, on='id', how='left')

        to_add['description_music'] = to_add['description'].apply(self.pull_artist_and_song)
        to_add['song_otd'] = to_add['description'].apply(self.pull_song)
        to_add['artist'] = to_add['description'].apply(self.pull_artist)
        
        self.updated_data = pd.concat([to_add, existing_data])

        cols_need = {
            # "elev_high",
            # "max_speed",
            # "average_watts",
            # "distance",
            # "kilojoules",
            # "max_heartrate",
            # "average_heartrate",
            # "max_watts",
            "date_str":"Date",
            "time_mins":"Time (minutes)",
            "distance_miles":"Distance (miles)",
            "pace_formatted":"Pace (minutes per mile)",
            # "start_lat",
            # "start_long",
            # "end_lat",
            # "end_long",
            "description":"Description",
            "description_music":"Music for the run",
        }


        formatted_strs = []
        
        # cutting dates for 2025..bad!
        for idx, row in self.updated_data[self.updated_data['start_date'] >= pd.Timestamp('2025-01-01').date()].iterrows():
            string = """
            --------------------
            """
            for col in cols_need.keys():
                string += f"""
                {cols_need[col]} : {row[col]}
                """
            string += """
            --------------------
            \n
            """
            formatted_strs.append(string)
            
        self.formatted_strs = formatted_strs
    
    def overwrite_data(self):
        self.updated_data.to_csv(self.file_name)
        with open("formatted_strs.txt", "w") as file:
            file.write(" ".join(self.formatted_strs))

    def read_data(self):
        return pd.read_csv(self.file_name)

class StravaML(StravaAPI):
    def __init__(self, client_id, client_secret, code=None):
        super().__init__(client_id, client_secret, code)