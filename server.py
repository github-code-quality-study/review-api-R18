import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk.corpus import stopwords
from urllib.parse import parse_qs, urlparse
import json
import pandas as pd
from datetime import datetime
import uuid
import os
from typing import Callable, Any
from wsgiref.simple_server import make_server

nltk.download('vader_lexicon', quiet=True)
nltk.download('punkt', quiet=True)
nltk.download('averaged_perceptron_tagger', quiet=True)
nltk.download('stopwords', quiet=True)

adj_noun_pairs_count = {}
sia = SentimentIntensityAnalyzer()
stop_words = set(stopwords.words('english'))

reviews = pd.read_csv('data/reviews.csv').to_dict('records')

class ReviewAnalyzerServer:
    def __init__(self) -> None:
        # This method is a placeholder for future initialization logic
        pass

    def analyze_sentiment(self, review_body):
        sentiment_scores = sia.polarity_scores(review_body)
        return sentiment_scores

    def get_data_filter_by_location(self, location, reviews):
        location_filter_list = []

        for review in reviews:
            if review['Location'] == location: 
                location_filter_list.append(review)

        return location_filter_list

    def get_data_filter_by_start_date(self, start_date, reviews):
        start_date_filter_list = []

        for review in reviews:
            review_date_time = datetime.strptime(review['Timestamp'], "%Y-%m-%d %H:%M:%S")
            start_date_time = datetime.strptime(start_date, '%Y-%m-%d')

            if review_date_time >= start_date_time: 
                start_date_filter_list.append(review)

        return start_date_filter_list

    def get_data_filter_by_end_date(self, end_date, reviews):
        end_date_filter_list = []

        for review in reviews:
            review_date_time = datetime.strptime(review['Timestamp'], "%Y-%m-%d %H:%M:%S")
            end_date_time = datetime.strptime(end_date, '%Y-%m-%d')

            if review_date_time <= end_date_time: 
                end_date_filter_list.append(review)

        return end_date_filter_list

    def get_data_filter_by_start_end_date(self, start_date, end_date, reviews):
        filter_start_date = self.get_data_filter_by_start_date(start_date, reviews)

        filter_end_date = self.get_data_filter_by_end_date(end_date, filter_start_date)
        
        return filter_end_date


    def sentimentize(self, reviews_list):
        sentimen_reviews = []
        for review in reviews_list:
            review['sentiment'] = self.analyze_sentiment(review['ReviewBody'])

            sentimen_reviews.append(review)

            sentimen_reviews = sorted(sentimen_reviews, key=lambda x: x['sentiment']['compound'], reverse=True)

        return sentimen_reviews

    def __call__(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> bytes:
        """
        The environ parameter is a dictionary containing some useful
        HTTP request information such as: REQUEST_METHOD, CONTENT_LENGTH, QUERY_STRING,
        PATH_INFO, CONTENT_TYPE, etc.
        """

        if environ["REQUEST_METHOD"] == "GET":
            # Create the response body from the reviews and convert to a JSON byte string
            response_body = json.dumps(reviews, indent=2).encode("utf-8")
            
            # Write your code here

            # Filtered by Locations List
            filter_locations_list = [
                'Albuquerque, New Mexico', 'Carlsbad, California', 'Chula Vista, California', 'Colorado Springs, Colorado',
                'Denver, Colorado', 'El Cajon, California', 'El Paso, Texas', 'Escondido, California', 'Fresno, California',
                'La Mesa, California', 'Las Vegas, Nevada', 'Los Angeles, California', 'Oceanside, California', 'Phoenix, Arizona',
                'Sacramento, California', 'Salt Lake City, Utah', 'Salt Lake City, Utah', 'San Diego, California', 'Tucson, Arizona'
            ]

            # Get Query String
            query_string = str(environ['QUERY_STRING'])

            
            # Get Valz from Query String
            query_string_valz = parse_qs(query_string)

            # Filter Data By Location ?location=cool-location
            try:
                location = query_string_valz['location'][0]
            
                data_filter_by_location = self.sentimentize(self.get_data_filter_by_location(location, reviews))
                response_body = json.dumps(data_filter_by_location, indent=2).encode("utf-8")
            except Exception as e:
                pass


            # Filter Data By Start Date ?start_date=start_date
            try:
                start_date = query_string_valz['start_date'][0]
            
                data_filter_by_start_date = self.sentimentize(self.get_data_filter_by_start_date(start_date, reviews))
                response_body = json.dumps(data_filter_by_start_date, indent=2).encode("utf-8")
            except Exception as e:
                pass


            # Filter Data By End Date ?end_date=end_date
            try:
                end_date = query_string_valz['end_date'][0]
            
                data_filter_by_end_date = self.sentimentize(self.get_data_filter_by_end_date(end_date, reviews))
                response_body = json.dumps(data_filter_by_end_date, indent=2).encode("utf-8")
            except Exception as e:
                pass


             # Filter Data By Start Date & End Date ?start_date=start_date&end_date=end_date
            try:
                start_date = query_string_valz['start_date'][0]
                end_date = query_string_valz['end_date'][0]
            
                data_filter_by_start_end_date = self.sentimentize(self.get_data_filter_by_start_end_date(start_date, end_date, reviews))
                response_body = json.dumps(data_filter_by_start_end_date, indent=2).encode("utf-8")
            except Exception as e:
                pass


            # Set the appropriate response headers
            start_response("200 OK", [
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(response_body)))
            ])
            
            return [response_body]


        if environ["REQUEST_METHOD"] == "POST":
            # Write your code here

            # Get Request Body Size
            try:
                request_body_size = int(environ.get('CONTENT_LENGTH', 0))
            except Exception as e:
                request_body_size = 0

            request_body = environ['wsgi.input'].read(request_body_size)
            data_params = parse_qs(request_body)

            ReviewId =  str(uuid.uuid4())
            Location = ""
            ReviewBody = ""

            try:
                Location = str(data_params[b'Location'][0].decode('utf-8'))
                ReviewBody = str(data_params[b'ReviewBody'][0].decode('utf-8'))
            except Exception as e:
                print ("Exception : " + str(e) )

                # Handling Exception with 400 Response
                if Location == "" or ReviewBody == "":
                    review_response = {
                        "ReviewBody": ReviewBody,
                        "Location": Location,
                        "Status": "Missing Location / ReviewBosy" 
                    }

                    response_body = json.dumps(review_response, indent=2).encode("utf-8")
                    
                    start_response("400 OK", [
                        ("Content-Type", "application/json"),
                        ("Content-Length", str(len(response_body)))
                    ])
                    
                    return [response_body]
            
            if "Cupertino" in Location:
                review_response = {
                    "Location": Location,
                    "Status": "Invalid Location" 
                }

                response_body = json.dumps(review_response, indent=2).encode("utf-8")
                
                start_response("400 OK", [
                    ("Content-Type", "application/json"),
                    ("Content-Length", str(len(response_body)))
                ])
                
                return [response_body]

            now_date_time = datetime.now()
            timestamp_d = str(now_date_time).split('.')[0]

            review_created = {
                "ReviewId": ReviewId,
                "ReviewBody": ReviewBody,
                "Location": Location,  
                "Timestamp": timestamp_d 
            }

            response_body = json.dumps(review_created, indent=2).encode("utf-8")

            # print(review_created)            
            # return [review_created]
            start_response("201 OK", [
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(response_body)))
            ])
            
            return [response_body]


if __name__ == "__main__":
    app = ReviewAnalyzerServer()
    port = os.environ.get('PORT', 8000)
    with make_server("", port, app) as httpd:
        print(f"Listening on port {port}...")
        httpd.serve_forever()