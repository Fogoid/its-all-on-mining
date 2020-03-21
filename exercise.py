import sys
import re
import queue

#########################
### A: AGENT BEHAVIOR ###
#########################

def roundNumber(num):
    m = (num * 1000) % 10
    if m >= 5:
        num += (10 - m) / 1000
    return num

class Observation:
    def __init__(self, utility, step):
        self.utility = utility
        self.step = step

class Agent:
    
    def __init__(self, options):
        # Regex to decide which type of configurations there are
        self.cycle = int(re.search(r"cycle=\d+( |\n|\r\n)", options).group(0)[len("cycle="):])
        self.decision = re.search(r"decision=[\w-]+( |\n|\r\n)", options).group(0)[len("decision="):].strip(" \r\n")
        
        restart = re.search(r"restart=\d+( |\n||\r\n)", options)
        self.restart = 0 if restart is None else int(restart.group(0)[len("restart="):].strip(" \r\n"))

        memoryFactor = re.search(r"memory-factor=\d+\.\d+( |\n|\r\n)", options)
        self.memoryFactor = 0.0 if memoryFactor is None else float(memoryFactor.group(0)[len("memory-factor="):].strip(" \r\n"))
        
        agents = re.search(r"agents=\[\w\d(,\w\d)*\]( |\n|\r\n)", options)
        self.agents = None if agents is None else agents.group(0)[len("agents="):].strip(" \r\n")

        # Dictionary where the expected utilities of each task observed is kept
        self.tasks = {}
        # list with a tuple with Observations made for each task
        self.observations = {}
        #A counter of how many taks exist
        self.numTasks = 0
        #The total gain of performing the selected tasks
        self.gain = 0
        #The last task executed
        self.preparing = -1
        #The step the agent is at
        self.currentStep = 0
        # task to which we are expecting ann observation
        self.expectedObsTasks = queue.Queue()

    def perceive(self, perception):
        p = perception.split(' ')
        if "A" not in perception:
            newTask = [float(p[1][len("u="):]), self.restart]
            if self.decision == "flexible":
                newTask += [float(p[1][len("u="):])]
            self.tasks[int(p[0][1:])] = newTask
        
        else: # It is an observation
            observations = []
            if self.decision == "flexible" and "," in p[1]:
                observations = self.multiple_observations(p[1])
            else:
                utiObserved = float(p[1][len("u="):])
                taskObs = self.expectedObsTasks.get()
                observations += [(taskObs, utiObserved, 1)]

            for taskObs, utiObserved, percentage in observations:
                if self.decision == "flexible" and self.tasks[taskObs][2] > utiObserved:
                    self.tasks[taskObs][2] = utiObserved

                if taskObs in self.observations.keys():
                    self.observations[taskObs] += [Observation(utiObserved, self.currentStep)]
                else:
                    self.observations[taskObs] = [Observation(utiObserved, self.currentStep)]
                
                # Calculate the new Expected Utility for the task
                eu = 0
                stepSums = 0
                for obs in self.observations[taskObs]:
                    eu += (obs.step ** self.memoryFactor) * obs.utility
                    stepSums += obs.step ** self.memoryFactor
                eu /= stepSums

                self.tasks[taskObs][0] = eu
                self.gain += utiObserved * percentage

            return utiObserved

    def decide_act(self):
        best_utility = -1
        secondBest = -1

        toExecute = -1
        for i in self.tasks.keys():
            meu = self.tasks[i][0] * (self.cycle - (self.currentStep + self.tasks[i][1]))
            better_one = False if toExecute == -1 else self.decision == "flexible" and self.tasks[i][2] < 0 and self.tasks[i][2] > self.tasks[toExecute][2] and meu > secondBest
            if (meu > best_utility or better_one):
                best_utility = meu
                toExecute = i

            if (meu > secondBest and meu < best_utility):
                secondBest = meu

        if toExecute == -1:
            self.currentStep += 1
            return -1, -1

        #Choose another decision with this one and dedicate a percentage to it
        if self.decision == "flexible" and self.tasks[toExecute][2] < 0:
            return self.multiple_tasks(toExecute)

        #Normal execution when there is no flexible agents
        if toExecute != self.preparing:
            if self.preparing != -1:
                self.tasks[self.preparing][1] = self.restart
            self.preparing = toExecute
        
        
        if self.tasks[self.preparing][1] == 0:
            self.expectedObsTasks.put(self.preparing)
        
        prepTime = self.tasks[self.preparing][1]
        self.tasks[self.preparing][1] -= (1 if self.tasks[self.preparing][1] > 0 else 0)
        
        self.currentStep += 1

        return self.preparing, prepTime

    def recharge(self):
        output = "state={"
        for i in self.tasks.keys():
            output += 'T%d=' % (i) + (('%.2f,' % (self.tasks[i][0])) if i in self.observations.keys() else "NA,")

        return output[:-1] + '} gain=%.2f' % (self.gain)

    def multiple_tasks(self, firstTask):
        best_utility = -1

        toExecute = -1
        for i in self.tasks.keys():
            if i == firstTask or self.tasks[i][2] <= 0:
                continue
            meu = self.tasks[i][0] * (self.cycle - (self.currentStep + self.tasks[i][1]))
            if (meu > best_utility):
                best_utility = meu
                toExecute = i

        total = self.tasks[toExecute][0] - self.tasks[firstTask][2]
        firstPer = self.tasks[toExecute][0] / total
        secondPer = - self.tasks[firstTask][2] / total
        execOrder = [(firstTask, firstPer),(toExecute, secondPer)]
        execOrder.sort(key=lambda x: x[0])
        self.expectedObsTasks.put(execOrder)

        execOrder = [(firstTask, roundNumber(firstPer)),(toExecute, 1 - roundNumber(firstPer))]
        execOrder.sort(key=lambda x: x[0])
        sys.stdout.write("{{T{}={:.2f},T{}={:.2f}}}\n".format(execOrder[0][0], execOrder[0][1], execOrder[1][0], execOrder[1][1]))

        self.currentStep += 1

    def multiple_observations(self, perception):
        [(firstTask, fper), (secondTask, sper)] = self.expectedObsTasks.get()

        [fObs,sObs] = re.sub(r"T\d+=", "", perception[3:-2]).split(",")

        return [(firstTask, float(fObs), fper), (secondTask, float(sObs), sper)]

class MultiAgent:

    def __init__(self, options):
        self.decision = re.search(r"decision=[\w-]+( |\n|\r\n)", options).group(0)[len("decision="):].strip(" \r\n")
        self.cycle = int(re.search(r"cycle=\d+( |\n|\r\n)", options).group(0)[len("cycle="):])

        restart = re.search(r"restart=\d+( |\n||\r\n)", options)
        self.restart = 0 if restart is None else int(restart.group(0)[len("restart="):].strip(" \r\n"))
        
        memoryFactor = re.search(r"memory-factor=\d+\.\d+( |\n|\r\n)", options)
        self.memoryFactor = 0.0 if memoryFactor is None else float(memoryFactor.group(0)[len("memory-factor="):].strip(" \r\n"))

        concurrencyPenalty = re.search(r"concurrency-penalty=\d+( |\n|\r\n)", options)
        self.concurrencyPenalty = 0 if concurrencyPenalty is None else int(concurrencyPenalty.group(0)[len("concurrency-penalty="):].strip(" \r\n"))

        self.currentStep = 0
        self.gain = 0.0

        self.numberOftasks = 0
        
        agents = re.search(r"agents=[\[\{]\w\d(,\w\d)*[\}\]]( |\n|\r\n)", options)
        self.agentsNames = agents.group(0)[len("agents="):].strip("}}][{{ \r\n").split(",")
        self.agents = {}
        for a in self.agentsNames:
            self.agents[a] = Agent(options)
        self.expectedObsTasks = queue.Queue()

        if self.decision == "homogeneous-society":
            self.observations = {}

            for a in self.agents.keys():
                self.agents[a].observations = self.observations

    def perceive(self, perception):
        p = perception.split(' ')
        if ("T" in perception): #GIVE THE NEW TASK TO ALL THE AGENTS
            for a in self.agentsNames:
                self.agents[a].tasks[int(p[0][1:])] = [float(p[1][len("u="):]), self.restart]
                self.numberOftasks += 1
        else:
            task = self.expectedObsTasks.get()
            if self.decision == "homogeneous-society": #GIVE THE OBSERVATION TO ALL THE AGENTS
                self.agents[p[0]].expectedObsTasks.get()
                self.add_observation(task, float(p[1][len("u="):]))
            else: #JUST GIVE TO THE CORRESPONDANT AGENT
                self.gain += self.agents[p[0]].perceive(perception)

    def add_observation(self, task, observation):
        if task in self.observations.keys():
            self.observations[task] += [Observation(observation, self.currentStep)]
        else:
            self.observations[task] = [Observation(observation, self.currentStep)]
        
        # Calculate the new Expected Utility for the task
        eu = 0
        stepSums = 0
        for obs in self.observations[task]:
            eu += (obs.step ** self.memoryFactor) * obs.utility
            stepSums += obs.step ** self.memoryFactor
        eu /= stepSums

        for a in self.agents:
            self.agents[a].tasks[task][0] = eu
        self.gain += observation

    def decide_act(self):
        numberOfAgents = len(self.agentsNames)
        allTasks = [None]*numberOfAgents
        for i in range(numberOfAgents):
            newValue = ()
            for k, v in self.agents[self.agentsNames[i]].tasks.items():
                newValue += ([k,] + v,)
            allTasks[i] = newValue

        firstValues = list((x,) for x in allTasks[0])

        permutations = self.get_permutations(allTasks[1:], firstValues)
        bestCombination = self.get_best_combination(permutations)

        for i in range(numberOfAgents):
            self.agents[self.agentsNames[i]].currentStep += 1
            
            if (bestCombination[i][1] <= 0):
                continue

            if self.agents[self.agentsNames[i]].preparing != bestCombination[i][0]:
                lastPrepared = self.agents[self.agentsNames[i]].preparing
                if lastPrepared != -1:
                    self.agents[self.agentsNames[i]].tasks[lastPrepared][1] = self.restart
                self.agents[self.agentsNames[i]].preparing = bestCombination[i][0]

            if bestCombination[i][2] == 0:
                self.expectedObsTasks.put(bestCombination[i][0])
                self.agents[self.agentsNames[i]].expectedObsTasks.put(bestCombination[i][0])
            else:
                self.agents[self.agentsNames[i]].tasks[bestCombination[i][0]][1] -= 1
            
        self.currentStep += 1
    
    def get_permutations(self, allTasks, permutations_made):
        newPermutations = []
        for i in permutations_made:
            for j in allTasks[0]:
                newPermutations += [i + (j,),]
                
        if allTasks[1:] == []:
            return newPermutations
        else:
            return self.get_permutations(allTasks[1:], newPermutations)
        
    def get_best_combination(self, permutations):
        bestCombination = ()
        bestGain = -1
        for p in permutations:
            tasksChosen = {}
            gain = 0
            biggerRestart = {}
            for [task, eu, restart] in p:
                if eu > 0:
                    gain += eu * (self.cycle - self.currentStep - restart)
                    if task in tasksChosen.keys():
                        tasksChosen[task] = tasksChosen[task] + 1
                        if restart > biggerRestart[task]:
                            biggerRestart[task] = restart
                    else:
                        tasksChosen[task] = 1
                        biggerRestart[task] = restart

            for v in tasksChosen.values():
                gain -= 0 if v == 1 else self.concurrencyPenalty * v * (self.cycle - self.currentStep - restart)
            if gain > bestGain:
                bestGain = gain
                bestCombination = p

        return bestCombination

    def recharge(self):
        output = "state={"
        for a in self.agentsNames:
            agentOutput = a + "={"
            for i in self.agents[a].tasks.keys():
                agentOutput += 'T%d=' % (i) + (('%.2f,' % (self.agents[a].tasks[i][0])) if i in self.agents[a].observations.keys() else "NA,")
            output += agentOutput[:-1] + "},"
        return output[:-1] + '} gain=%.2f' % (self.gain)
    

#####################
### B: MAIN UTILS ###
#####################

line = sys.stdin.readline()
agent = Agent(line) if "agents" not in line else MultiAgent(line)
for line in sys.stdin:
    if line.startswith("end"): break
    elif line.startswith("TIK"): agent.decide_act()
    else: agent.perceive(line)
sys.stdout.write(agent.recharge()+'\n')
