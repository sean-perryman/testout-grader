# CompTIA TestOut Grader
I run a Network+ course at a university, and found myself spending 30+ minutes every week manipulating the .CSV gradebook output that they provide so I can enter the grades into my LMS. 
This program automates that job and cuts the time investment down significantly.

## To Use
- Have Docker installed and working on your system
- Clone the repo and enter that directory
- docker build -t csv-grader .
- docker run -p 5000:5000 csv-grader

I will say, I am not a very saavy Docker user, but this seems to work nicely for my needs. 

Enjoy!
