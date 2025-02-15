import json
import subprocess
from shutil import copy
from os import path, listdir
import fnmatch
from subprocess import CalledProcessError

from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.web import Application, HTTPError, RequestHandler

from db.model import Teams, metadata
from scores import SCORES
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# setup database
engine = create_engine('sqlite:///teams.db')
Session = sessionmaker(bind=engine)
metadata.create_all(engine, checkfirst=True)
db = Session()

class Home(RequestHandler):
    def get(self):
        self.render("html/leaderboard.html")

class Leaderboard(RequestHandler):
    def get(self):
        teams = db.query(Teams).order_by(Teams.score.desc()).all()
        message = [team.as_dict() for team in teams]
        #message = [
        #    {"id": 0, "name": "bla", "score": 222},
        #    {"id": 1, "name": "bla2", "score": 22},
        #    {"id": 2, "name": "bla5", "score": 22},
        #    {"id": 3, "name": "bla52", "score": 22},
        #]
        self.write({'teams': message})

# TODO: add UUID
class Register(RequestHandler):
    def post(self):
        # get a team name
        submission = json.loads(self.request.body)
        # check if team name is already in use
        team = db.query(Teams).filter_by(name=submission['name']).first()

        response = {}

        if team:
            # return existing team id
            response['message'] = 'Team exists with ID {}'.format(team.id)
        else:
            # return new team id
            team = Teams(name=submission['name'])
            db.add(team)
            db.commit()
            response['message'] = 'Successfully added team {} with ID {}'.format(team.name, team.id)

        response['id'] = team.id
        response['name'] = team.name

        self.write(response)

class Score(RequestHandler):
    def get(self):
        id = self.get_argument('id', None)
        team = db.query(Teams).filter_by(id=id).first()
        if not team: raise HTTPError(404)
        self.write({'id': team.id, 'team': team.as_dict()})

class Hint(RequestHandler):
    def get(self):
        # team id
        id = self.get_argument('id', None)
        # request a testcase
        case = self.get_argument('case', None)

        if not id: raise HTTPError(404, "Need a team ID")
        if not case: raise HTTPError(404, "Need a case submission")
        
        # update the hint for the user
        team = db.query(Teams).filter_by(id=id).first()
        setattr(team, "hint{}".format(case), True)
        db.commit()

        # retrieve the hint file
        try:
            for file in listdir(path.join("testfiles")):
                if fnmatch.fnmatch(file, '{}*'.format(case)):
                    with open(path.join("testfiles", file)) as test_file:
                        content = test_file.read()
                        file_name = file

                    self.write({'case': case, 'name': file_name, 'content': content})
                    break
        except FileNotFoundError:
            raise HTTPError(500, "Requested test case not found")


    
class Submit(RequestHandler):
    def post(self):
        # get the contract
        submission = json.loads(self.request.body)
        # check if team exists
        team = db.query(Teams).filter_by(id=submission['id']).first()

        response = {}

        if team and submission['results']:
            response['message'] = "Submitted results for team {}".format(team.name)
            update_score(team, submission['results'])
        elif team:
            response['message'] = "Please submit your results"
        else:
            response['message'] = "Team ID not found"

        self.write(response)

# parse results and update score of the team
def update_score(team, results):
    team.submissions += 1
    # loop through the results
    total_score = 0
    for case, result in results.items():
        # if result is true update score
        # else leave score as is
        if result:
            # did team request hint?
            hint = getattr(team, "hint{}".format(case))
            score = SCORES[case]/2 if hint else SCORES[case]
            # SCORES is imported from "scores.py"
            total_score += score
            # update the score for the case
            setattr(team, "test{}".format(case), score)
    team.score = total_score
    db.commit()

# not used at the moment
def execute_test(test):
    try:
        output = subprocess.run(["truffle", "test"], stdout=subprocess.PIPE, check=True)
        result = output.stdout.rstrip()

        score = 0

        return score
    except CalledProcessError:
        raise HTTPError(500)

def make_app():
  urls = [
      ("/api/leaderboard", Leaderboard),
      ("/api/hint", Hint),
      ("/api/register", Register),
      ("/api/submit", Submit),
      ("/api/score", Score),
      ("/", Home)
      ]
  return Application(urls, debug=True)


def main():
    # setup Tornado
    app = make_app()
    app.listen(3000)
    # server = HTTPServer(app)
    # server.bind(3000)
    # server.start(0)
    IOLoop.current().start()

if __name__ == '__main__':
    main()
