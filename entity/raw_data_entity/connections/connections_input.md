Curl

curl -X GET "https://fakerestapi.azurewebsites.net/api/v1/Activities" -H  "accept: text/plain; v=1.0"
Request URL
https://fakerestapi.azurewebsites.net/api/v1/Activities
Server response
Code	Details
200	
Response body
Download
[
  {
    "id": 1,
    "title": "Activity 1",
    "dueDate": "2025-01-24T15:02:50.2415926+00:00",
    "completed": false
  },
  {
    "id": 2,
    "title": "Activity 2",
    "dueDate": "2025-01-24T16:02:50.2415957+00:00",
    "completed": true
  }]
