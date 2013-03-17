from jinja2 import Environment, FileSystemLoader
import json
import operator
import os
import os.path
import sys

# Constants for winners of these rounds (*not* the teams in each round)
FIRSTFOUR = 0
SECONDROUND = 1
THIRDROUND = 2
SWEETSIXTEEN = 3
ELITEEIGHT = 4
FINALFOUR = 5
CHAMPIONSHIP = 7

ROUNDNAMES = ["first four", "second round", "third round", "sweet sixteen",
              "elite eight", "final four", "championship game"]
ROUNDSCORES = [2**i for i in range(7)]
SEEDORDER = [1, 16, 8, 9, 5, 12, 4, 13, 6, 11, 3, 14, 7, 10, 2, 15]


class BracketValidationError(Exception):
    pass


def chunks(l, n):
    """
    Yield successive n-sized chunks from l.
    http://stackoverflow.com/a/312464/335888
    """
    for i in range(0, len(l), n):
        yield l[i:i+n]


def flatten(l):
    """
    Flatten a list that can contain non-lists.
    """
    x = []
    for i in l:
        if isinstance(i, list) or isinstance(i, tuple):
            x.extend(flatten(i))
        else:
            x.append(i)
    return x


def team_has_played(start, master, firstfour, team, round):
    """
    Determine if a team has played yet in round X. Returns True or False as
    expected.

    If a team would have played provided it got that far in the bracket this
    function still returns True. Generally you shouldn't call this function if
    that's the case, though.
    """
    if len(master) <= round:
        return False
    # First four
    if round == FIRSTFOUR:
        for matchup in [flatten(x) for x in chunks(firstfour, 2)]:
            if team in matchup:
                return sum([x in master[0] for x in matchup]) == 1
        return False
    # Other rounds
    else:
        for matchup in [flatten(x) for x in chunks(start, 2**round)]:
            if team in matchup:
                return sum([x in master[round] for x in matchup]) == 1
        return False


def validate_bracket(start, teams, firstfour, nextsixty, bracket,
                     incomplete=False):
    if not incomplete and len(bracket) < 7:
        raise BracketValidationError("bracket does not have 7 rounds")
    if incomplete and len(bracket) == 0:
        return
    # Validate first four
    if not incomplete or (incomplete and len(bracket[0]) == 4):
        for matchup in chunks(firstfour, 2):
            if sum([x in bracket[0] for x in flatten(matchup)]) != 1:
                msg = ("matchup {0} doesn't have exactly one winner in "
                       "first four".format(matchup))
                raise BracketValidationError(msg)
    # Validate further rounds
    if incomplete:
        end = len(bracket)
    else:
        end = 7
    for i in range(1, end):
        round = ROUNDNAMES[i]
        prevround = ROUNDNAMES[i - 1]
        if not incomplete or i + 1 != end:
            for matchup in chunks(start, 2**i):
                if sum([x in bracket[i] for x in flatten(matchup)]) != 1:
                    msg = "matchup {0} has no winner in {1}".format(matchup,
                                                                    round)
                    raise BracketValidationError(msg)
        for team in bracket[i]:
            if i != 1 or team in firstfour:
                if team not in bracket[i - 1]:
                    msg = ("{0} can't win in {1} without having won "
                           "in {2}".format(team, round, prevround))
                    raise BracketValidationError(msg)


def main():
    # Check what directory we're reading data from
    if len(sys.argv) != 2:
        sys.stderr.write("Usage: bracketeering.py FOLDER\n")
        sys.stderr.write("error: folder not specified\n")
        sys.exit(1)
    dir = sys.argv[1]
    # Validate that the directory exists
    try:
        files = os.listdir(dir)
    except OSError as e:
        sys.stderr.write("error: {0}: {1}\n".format(dir, e[1]))
        sys.exit(2)
    # Read in start.txt
    start = []
    teams = []
    firstfour = []  # actually eight
    nextsixty = []  # actually sixty
    teamnames = {}
    seeds = {}
    try:
        startfile = open(os.path.join(dir, 'start.txt'))
    except IOError as e:
        sys.stderr.write("error: {0}: {1}\n".format(
            os.path.join(dir, 'start.txt'), e[1]))
        sys.exit(2)
    lines = startfile.read().splitlines()
    startfile.close()
    i = 0
    for lineno in range(1, len(lines) + 1):
        line = lines[lineno - 1]
        if '/' in line:
            if len(line.split('/')) == 2:
                team1 = line.split('/')[0].split(' ', 1)
                team2 = line.split('/')[1].split(' ', 1)
                start.append([team1[0], team2[0]])
                teams.extend([team1[0], team2[0]])
                firstfour.extend([team1[0], team2[0]])
                if len(team1) == 2:
                    teamnames[team1[0]] = team1[1]
                else:
                    teamnames[team1[0]] = team1[0]
                if len(team2) == 2:
                    teamnames[team2[0]] = team2[1]
                else:
                    teamnames[team2[0]] = team2[0]
                seeds[team1[0]] = SEEDORDER[i]
                seeds[team2[0]] = SEEDORDER[i]
            else:
                sys.stderr.write("error: start.txt: line %d has multiple "
                                 "slashes\n" % lineno)
                sys.exit(2)
        else:
            if ' ' in line:
                team, teamname = line.split(' ', 1)
                teamnames[team] = teamname
            else:
                team = line
                teamnames[team] = team
            start.append(team)
            teams.append(team)
            nextsixty.append(team)
            seeds[team] = SEEDORDER[i]
        i += 1
        if i >= 16:
            i = 0
    if len(teams) != 68 or len(teamnames) != 68 or len(start) != 64:
        sys.stderr.write("error: start.txt: not enough teams\n")
        sys.exit(2)
    if len(firstfour) != 8:
        sys.stderr.write("error: start.txt: not enough first four games\n")
        sys.exit(2)
    # Read in master.json
    try:
        masterfile = open(os.path.join(dir, 'master.json'))
    except IOError as e:
        sys.stderr.write("error: {0}: {1}\n".format(
            os.path.join(dir, 'master.json'), e[1]))
        sys.exit(2)
    master = json.load(masterfile)
    masterfile.close()
    # Validate master.json
    try:
        validate_bracket(start, teams, firstfour, nextsixty, master, True)
    except BracketValidationError as e:
        sys.stderr.write("error: master.json: {0}\n".format(e))
        sys.exit(3)
    # Read in brackets
    brackets = {}
    for filename in files:
        if filename in ['start.txt', 'master.json']:
            continue
        if len(filename.split('.')) > 1 and filename.split('.')[-1] == 'json':
            name = '.'.join(filename.split('.')[:-1])
            try:
                bracketfile = open(os.path.join(dir, filename))
            except IOError as e:
                continue
            bracket = json.load(bracketfile)
            bracketfile.close()
            try:
                validate_bracket(start, teams, firstfour, nextsixty, bracket)
            except BracketValidationError as e:
                sys.stderr.write("error: {0}: {1}\n".format(filename, e))
                sys.exit(3)
            brackets[name] = bracket
    # Score brackets
    correct = {}
    scores = {}
    pointsp = {}
    totals = {}
    for name in brackets:
        correct[name] = []
        scores[name] = []
        pointsp[name] = 0
        roundcorrect = []
        roundscore = 0
        # Score first four
        for team in brackets[name][FIRSTFOUR]:
            if team_has_played(start, master, firstfour, team, FIRSTFOUR):
                if team in master[FIRSTFOUR]:
                    roundcorrect.append(True)
                    roundscore += ROUNDSCORES[FIRSTFOUR]
                    pointsp[name] += ROUNDSCORES[FIRSTFOUR]
                else:
                    roundcorrect.append(False)
            else:
                roundcorrect.append(None)
                pointsp[name] += ROUNDSCORES[FIRSTFOUR]
        correct[name].append(roundcorrect)
        scores[name].append(roundscore)
        # Score everything else
        for i in range(1, 7):
            roundcorrect = []
            roundscore = 0
            for team in brackets[name][i]:
                if i != SECONDROUND and team in brackets[name][i-1]:
                    if correct[name][i-1][brackets[name][i-1].index(team)] \
                       is False:
                        roundcorrect.append(False)
                        continue
                if team_has_played(start, master, firstfour, team, i):
                    if team in master[i]:
                        roundcorrect.append(True)
                        roundscore += ROUNDSCORES[i]
                        pointsp[name] += ROUNDSCORES[i]
                    else:
                        roundcorrect.append(False)
                else:
                    roundcorrect.append(None)
                    pointsp[name] += ROUNDSCORES[i]
            correct[name].append(roundcorrect)
            scores[name].append(roundscore)
        totals[name] = sum(scores[name])
    # Now rank everybody
    table = [(x, totals[x], pointsp[x]) for x in totals.keys()]
    for col in (2, 1):
        table = sorted(table, key=operator.itemgetter(col), reverse=True)
    ranks = []
    lastvalue = None
    lastrank = None
    i = 1
    for row in table:
        if row[1:3] == lastvalue:
            ranks.append((row[0], lastrank))
        else:
            ranks.append((row[0], i))
            lastvalue = row[1:3]
            lastrank = i
        i += 1
    # HTML o' doom
    outdir = os.path.join(dir, 'output')
    try:
        os.mkdir(outdir)
    except OSError as e:
        pass
    try:
        infile = open('style.css')
    except IOError as e:
        sys.stderr.write("error: {0}: {1}\n".format('style.css', e))
        sys.exit(2)
    try:
        outfile = open(os.path.join(outdir, 'style.css'), 'w')
    except IOError as e:
        sys.stderr.write("error: {0}: {1}\n".format('style.css', e))
        sys.exit(2)
    outfile.write(infile.read())
    infile.close()
    outfile.close()
    env = Environment(loader=FileSystemLoader('.'))
    rankstpl = env.get_template('rankings.html')
    try:
        outfile = open(os.path.join(outdir, 'index.html'), 'w')
    except IOError as e:
        sys.stderr.write("error: {0}: {1}\n".format('index.html', e))
        sys.exit(2)
    htmlvars = {
        'ranks': ranks,
        'scores': scores,
        'pointsp': pointsp,
    }
    html = rankstpl.render(**htmlvars)
    outfile.write(html)
    outfile.close()
    brackettpl = env.get_template('bracketpage.html')
    for name in brackets:
        try:
            outfile = open(os.path.join(outdir, name + '.html'), 'w')
        except IOError as e:
            sys.stderr.write("error: {0}: {1}\n".format(name + '.html', e))
            sys.exit(2)
        bracket = [list() for _ in range(8)]
        # handle rounds 0 (first four) and 1 (round of 64)
        counter = 0
        for team in start:
            if isinstance(team, list):
                for otherteam in team:
                    bracket[0].append({'team': otherteam,
                                       'teamname': teamnames[otherteam],
                                       'seed': seeds[otherteam],
                                       'won': otherteam in master[0],
                                       'correct': None,
                                       'winnerof': None})
                if team[0] in brackets[name][0]:
                    otherteam = team[0]
                else:
                    otherteam = team[1]
                bracket[1].append({'team': otherteam,
                                   'teamname': teamnames[otherteam],
                                   'seed': seeds[otherteam],
                                   'won': otherteam in master[1],
                                   'correct': correct[name][0][counter],
                                   'winnerof': (0, counter)})
                counter += 1
            else:
                bracket[1].append({'team': team,
                                   'teamname': teamnames[team],
                                   'seed': seeds[team],
                                   'won': team in master[1],
                                   'correct': None,
                                   'winnerof': None})
        for round in range(2, 8):
            for i in range(2**(7-round)):
                teams = [bracket[round-1][j]['team'] for j in (i*2, i*2+1)]
                if teams[0] in brackets[name][round-1]:
                    team = teams[0]
                elif teams[1] in brackets[name][round-1]:
                    team = teams[1]
                else:
                    bracket[round].append(None)
                    break
                if round < 7:
                    won = team in master[round]
                else:
                    won = False
                bracket[round].append({
                    'team': team,
                    'teamname': teamnames[team],
                    'seed': seeds[team],
                    'won': won,
                    'correct': correct[name][round-1][i],
                    'winnerof': (round-1, i),
                })
        htmlvars = {
            'name': name,
            'rank': dict(ranks)[name],
            'scores': scores[name],
            'pointsp': pointsp[name],
            'bracket': bracket,
            'seedorder': SEEDORDER,
        }
        html = brackettpl.render(**htmlvars)
        outfile.write(html)
        outfile.close()
    return
    try:
        outfile = open(os.path.join(outdir, 'chooser.html'), 'w')
    except IOError as e:
        sys.stderr.write("error: {0}: {1}\n".format('chooser.html', e))
        sys.exit(2)
    choosertpl = env.get_template('chooser.html')
    htmlvars = {
    }
    html = choosertpl.render(**htmlvars)
    outfile.write(html)
    outfile.close()

if __name__ == '__main__':
    main()
