from flask import Flask, render_template, request, jsonify
import os
import requests
from datetime import datetime, timedelta, time
import pytz
import pandas as pd

# def fetchIfNotExists(url, fileName):
#   if not os.path.exists(fileName):
#     print("Fetching course catalog from @illinois/courses-dataset...")
#     r = requests.get(url, stream=True)
#     with open(fileName, 'wb') as fd:
#       for chunk in r.iter_content(chunk_size=4096):
#         fd.write(chunk)

# # Ensure we have a GPA dataset and a courses dataset
# fetchIfNotExists("https://raw.githubusercontent.com/illinois/courses-dataset/master/course-schedule/2022-sp.csv", "courses.csv")

df_courses = pd.read_csv("courses.csv")
df_courses["Course"] = df_courses["Subject"] + df_courses["Number"].astype(str)
df_unique = df_courses.drop_duplicates(subset=['Course'])
options = {"course": df_unique["Course"].values.tolist(), "name": df_unique["Name"].values.tolist()}

def GET_subject_number(subject, number):
  # Prep result:
  result = { "course": f"{subject} {number}" }

  # Cast `number` as an int and ensure `subject` is all caps:
  try:
    number = int(number)
  except:
    result["error"] = f"Course number `{number}` is not a number"
    status_code = 404
    return jsonify(result), status_code
  subject = subject.upper()

  # Fetch data:
  courses = df_courses[ (df_courses["Subject"] == subject) & (df_courses["Number"] == number) & (df_courses["Start Time"] != "") & (df_courses["Start Time"] != "ARRANGED") ] 

  if len(courses) == 0:
    # Provide an error:
    result["error"] = f"No course data available for {subject} {number}"
    status_code = 404
  else:
    # Prefer LEC sections (for courses with discussions/labs)
    course_lec = courses[ courses["Type Code"] == "LEC" ]
    if len(course_lec) > 0:
      courses = course_lec

    # Get the first result's data:
    c = courses.iloc[0]
    result["Start Time"] = c["Start Time"]
    result["Days of Week"] = c["Days of Week"]
    status_code = 200

  return jsonify(result), status_code

app = Flask(__name__, static_folder="static", template_folder="templates")

# Route for "/" (frontend):


@app.route('/')
def index():
    return render_template("index.html", options=options)


# Route for "/weather" (middleware):
@app.route('/weather', methods=["POST"])
def POST_weather():
    course = request.form["course"]
    course = course.replace(" ", "")
    sub = course[:-3].upper()
    num = course[-3:]
    result, status_code = GET_subject_number(sub, num)
    if status_code != 200:
        res_list = result.get_json()
        report = {"course": f"{sub} {num}"}
        error = res_list["error"]
        report["error"] = f"{error}"
        return jsonify(report), 400
    met_weekday = list(result.get_json()["Days of Week"])
    met_hour, met_min = result.get_json()["Start Time"].split(":")
    if met_hour != "12" and met_min.split(" ")[1] == "PM":
        met_hour = int(met_hour) + 12
    met_min = met_min.split(" ")[0]
    weekday_dic = {'M': 0, 'T': 1, 'W': 2, 'R': 3, 'F': 4}
    cour_weekday = []
    for i in range(len(met_weekday)):
        cour_weekday.append(weekday_dic.get(met_weekday[i]))
    dt1 = datetime.now(pytz.timezone('America/Chicago'))
    today_weekday = dt1.weekday()
    today_hour = dt1.hour
    print(dt1, today_weekday, dt1.hour)
    day_diff = -1
    for j in range(len(cour_weekday)):
        if today_weekday <= cour_weekday[j]:
            day_diff = cour_weekday[j] - today_weekday
            break
    if day_diff < 0:
        for a in range(len(cour_weekday)):
            if today_weekday < (cour_weekday[a]+7):
                day_diff = (cour_weekday[a]+7) - today_weekday
                break
    elif day_diff == 0 and today_hour > int(met_hour):
        for a in range(len(cour_weekday)):
            if today_weekday < (cour_weekday[a]+7):
                day_diff = (cour_weekday[a]+7) - today_weekday
                break
    hour_diff = -1
    if today_hour <= int(met_hour):
        hour_diff = int(met_hour) - today_hour
    else:
        hour_diff = int(met_hour) + 24 - today_hour
        day_diff = day_diff - 1
    print(day_diff, hour_diff)
    total_diff = day_diff * 24 + hour_diff
    dt2 = dt1 + timedelta(days=day_diff, hours=hour_diff)
    print(total_diff)
    print(dt2)
    wea_fore = requests.get('https://api.weather.gov/points/40.1125,-88.2284')
    wea_link = wea_fore.json()["properties"]["forecastHourly"]
    wea_report = requests.get(wea_link)
    if total_diff <= 144:
        temperature = wea_report.json(
        )["properties"]["periods"][total_diff]["temperature"]
        temperature = int(temperature)
        forecast = wea_report.json(
        )["properties"]["periods"][total_diff]["shortForecast"]
        fore_time = wea_report.json(
        )["properties"]["periods"][total_diff]["startTime"][:19].replace("T", " ")
        print(fore_time)
    else:
        temperature = "forecast unavailable"
        forecast = "forecast unavailable"
        fore_time = f"{dt2.date()} {dt2.hour}:00:00"
    report = {"course": f"{sub} {num}"}
    report["nextCourseMeeting"] = f"{dt2.date()} {dt2.hour}:{met_min}:00"
    report["forecastTime"] = f"{fore_time}"
    report["temperature"] = temperature
    report["shortForecast"] = f"{forecast}"
    print(report)
    status_code = 200
    return jsonify(report), status_code

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8080)