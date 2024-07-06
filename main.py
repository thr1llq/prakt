import requests
from bs4 import BeautifulSoup as bs
import pymysql.cursors
from flask import Flask, render_template, request


app = Flask(__name__, static_folder='static')

def insert_data_to_mysql(connection, vacancy_data, link):
    with connection.cursor() as cursor:
        insert_query = "INSERT INTO user2 (`Job Title`, `Company`, `Location`, `Skills`, `Salary`, `Link`) VALUES (%s, %s, %s, %s, %s, %s)"
        try:
            cursor.execute(insert_query, (
                str(vacancy_data['title'][:32]).replace('\x00', ''),
                str(vacancy_data['name_company'][:32]).replace('\x00', ''),
                str(vacancy_data['location'][:32]).replace('\x00', ''),
                str(vacancy_data['requirements'][:32]).replace('\x00', ''),
                str(vacancy_data['salary'][:32]).replace('\x00', ''),
                str(link).replace('\x00', '')
            ))
            connection.commit()  
        except pymysql.err.DataError as e:
            print(f"Error inserting data: {e}")


def connect_to_mysql():
    connection = pymysql.connect(
        host='localhost',  
        port=3306,
        user='root',  
        password='FrotLig13',  
        database='prakt',
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )

    reset_mysql_table(connection)  

    return connection

def reset_mysql_table(connection):
    with connection.cursor() as cursor:
        drop_query = "DROP TABLE IF EXISTS `user2`;"
        create_table_query = """CREATE TABLE user2 (
          `id` int(11) NOT NULL AUTO_INCREMENT,
          `Job Title` varchar(255),
          `Company` varchar(255),
          `Location` varchar(255),
          `Skills` varchar(255),
          `Salary` varchar(255),
          `Link` text,
          PRIMARY KEY (`id`)
        ) ENGINE=InnoDB;
        """
        print("Dropping table `user2`...")
        cursor.execute(drop_query)
        print("Creating table `user2`...")
        cursor.execute(create_table_query)
        print("Table `user2` created.")

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/search', methods=['POST'])
def search():
    position = request.form.get('position', '').lower()
    city = request.form.get('city', '').lower()
    work_type = request.form.get('work_type', '').lower()
    skills = request.form.get('skills', '').lower()
    company = request.form.get('company', '').lower()
    salary = request.form.get('salary', '').lower()

    total_vacancies, filtered_vacancies = parse_and_filter_vacancies(position, city, work_type, skills, company, salary)

    return render_template("next.html", vacancies=filtered_vacancies, total_vacancies=total_vacancies)

def parse_and_filter_vacancies(position, city, work_type, skills, company, salary):
    filtered_vacancies = []
    connection = connect_to_mysql()

    URL_T = "https://career.habr.com/vacancies?type=all"
    page_num = 1

    while True:
        url = f"{URL_T}&page={page_num}"
        r = requests.get(url)
        soup = bs(r.text, "html.parser")
        vacancies = soup.find_all('div', class_='vacancy-card__inner')

        if not vacancies:
            break

        for vacancy in vacancies:
            vacancy_data = {
                'title': vacancy.find('a', class_='vacancy-card__title-link').text.strip().lower(),
                'location': vacancy.find('div', class_='vacancy-card__meta').text.strip().lower(),
                'requirements': vacancy.find('div', class_='vacancy-card__skills').text.strip().lower() if vacancy.find('div', class_='vacancy-card__skills') else '',
                'name_company': vacancy.find('div', class_='vacancy-card__company-title').text.strip().lower(),
                'salary': vacancy.find('div', class_='vacancy-card__salary').text.strip().lower()
            }

            if (
                (not position or position in vacancy_data['title']) and
                (not city or city in vacancy_data['location']) and
                (not work_type or work_type in vacancy_data['location']) and
                (not skills or all(skill.strip() in vacancy_data['requirements'] for skill in skills.split(','))) and
                (not company or company in vacancy_data['name_company'])
            ):
                link = 'https://career.habr.com' + vacancy.find('a', class_='vacancy-card__title-link')['href']
                filtered_vacancies.append({'title': vacancy_data["title"],
                    'name_company': vacancy_data["name_company"],
                    'location': vacancy_data["location"],
                    'requirements': vacancy_data["requirements"],
                    'salary': vacancy_data["salary"],
                    'url': link
                })

                insert_data_to_mysql(connection, vacancy_data, link)

        page_num += 1

    connection.close()
    return len(filtered_vacancies), filtered_vacancies

if __name__ == "__main__":
    connection = connect_to_mysql()
    reset_mysql_table(connection)
    app.run(debug=True, host='0.0.0.0')
