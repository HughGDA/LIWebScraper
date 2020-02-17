from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from requests import get, post
from dotenv import load_dotenv
from pyvirtualdisplay import Display
from datetime import date
import os
import time

# replace with your module Full URL
module_url = "[Full URL Here]"

# import email and password for LinkedIn from .env file
def email_and_pass():
        load_dotenv() # load environment variables from '.env' file
        user_email = os.getenv('LI_EMAIL')
        user_pass = os.getenv('LI_PASS')
        return user_email, user_pass

# start the virtual diaplay for the headless browser
def start_display(width=1366, height=768):
        display = Display(visible=0, size=(width, height))
        display.start()
        return display

# start the browser as 'driver'
def start_driver(width=1366, height=768):
        driver = webdriver.Firefox()
        driver.set_window_size(width, height)
        driver.set_script_timeout(45)
        driver.set_page_load_timeout(45)
        driver.implicitly_wait(20)
        return driver

# login to LinkedIn and return the driver
def linked_in_login(driver, email, passw, login_url = 'https://www.linkedin.com/login?trk=guest_homepage-basic_nav-header-signin'):
        driver.get(login_url)
        print('Login page found successfully')
        driver.find_element_by_id("username").send_keys(email)
        driver.find_element_by_id("password").send_keys(passw)
        driver.find_elements_by_tag_name("button")[0].click()
        print('Login entry confirmed')
        print('Redirecting to first post...')
        return driver

# using the api, retrieve batches of links to LinkedIn posts
def get_posts_data(api_url = module_url+'posts'):
        json_data = get(api_url).json()
        posts = json_data['items']
        # if there are more posts after this batch, find the url for the next batch within the retreived JSON
        if json_data['hasMore']:
                for link in json_data['links']:
                        if link['rel'] == 'next':
                                next_api_url = link['href']
                                return posts, next_api_url
        # else just return the current batch of posts
        else:
                return posts, False

# scrape the retrieved post urls
def post_scraping(driver, li_url, first_try = True):
        try:
                driver.get(li_url)
                # scrape the data for reactions and views
                reacts = driver.find_elements_by_class_name("social-details-social-counts__reactions-count")
                lists = driver.find_elements_by_xpath("//span//strong")
                # for reactions and views if a number has been obtained cast it to an int, else return 0
                if len(lists) > 0:
                        views = int(lists[0].get_attribute("innerHTML")[0:-6].replace(",","")) # remove any commas in number string to cast to int
                else:
                        views = 0
                if len(reacts) > 0:
                        react = int(reacts[0].get_attribute("innerHTML").replace(",","")) # remove any commas in number string to cast to int
                else:
                        react = 0
        # try to log a post twice before abandoning
        except Exception as what_went_wrong:
                # if an exception is encountered print the exception and try a second time
                if first_try:
                        print(str(what_went_wrong)+' on: ' + li_url + '.  Action: retrying.')
                        driver = post_scraping(driver, li_url, first_try = False)
                # if this is the second attempt, abandon and move to the next post
                else:
                        print(str(what_went_wrong)+' on: ' + li_url + '.  Action: Second Exception, abandoning...')
                return driver
        # group together the data to be sent via API
        data = {
                'GETREACT':react,
                'GETVIEW':views,
                'GETURL':li_url
                }
        response = post(url = module_url+'posts', data = data)
        # print whether the data was logged to the database on the first or second attemp
        if(first_try):
                print(li_url+' response: '+str(response.status_code))
        else:
                print('Second Attempt: '+li_url+' response: '+str(response.status_code))
        # if the response code is not 200 (i.e. a failed attempt) retry on attempt 1, abandon on attempt 2
        if response.status_code != 200 and first_try:
                print(response.reason)
                post_scraping(driver, li_url, first_try = False)
        elif response.status_code != 200:
                print('(Second Exception) Status Code '+str(response.status_code)+' encountered on: ' + li_url + ', abandoning...')
        return driver

# function to quit previous driver and start a new one
def change_driver(driver, email, passw):
        driver.quit()
        new_driver = start_driver()
        new_driver = linked_in_login(new_driver, email, passw)
        return new_driver

# loop to scrape until all posts have been checked
def scraping_loop(driver, posts, next_api_url, email, passw):
        while True:
                for post in posts:
                        driver = post_scraping(driver, post['url'])
                # if false indicates that there are no more posts
                if next_api_url == False:
                        return driver
                print('Change to New Driver')
                driver = change_driver(driver, email, passw)
                posts, next_api_url = get_posts_data(next_api_url)

# main function
def main():
        try:
                # print out date of scraping
                print("\n\nScraping start: "+str(date.today()))
                email, passw = email_and_pass()
                display = start_display()
                driver = start_driver()
                driver = linked_in_login(driver, email, passw)
                posts, next_api_url = get_posts_data()
                driver = scraping_loop(driver, posts, next_api_url, email, passw)
        # if an exception is encountered that cannot be handled by the try... except within scrpaing_loop(), print exception and stop python execution
        except Exception as e:
                print("EXCEPTION ENCOUNTERED IN MAIN LOOP")
                print(str(e))
        # always stop the dispay and driver to free up system resources and avoid zombie processes
        finally:
                try:
                        display.stop()
                        print("Scraping finished, with display stop successful")
                except:
                        print("Error in stopping display.")
                try:
                        driver.quit()
                        print("Scraping finished, with driver quit successful")
                except:
                        print("Error in quitting driver.")

main()
