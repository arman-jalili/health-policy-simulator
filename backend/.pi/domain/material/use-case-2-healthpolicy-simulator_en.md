# Use Case 2: HealthPolicy Simulator

## Target vision of the use case

The goal is to develop a transparent AI agent simulation system for the Austrian healthcare and social system, in which autonomous institutional AI agents represent relevant stakeholders, independently discuss, negotiate and evaluate complex questions, and produce comprehensible compromises and recommendations for action. The human user does not merely receive a result, but complete insight into the lines of argument, conflicts, negotiations and consensus-building processes of the AI agents involved.

This turns AI from a pure analysis tool into a strategic multi-agent simulator for political, organisational and financial decisions in the healthcare sector.

## Core idea: a multi-agent system for negotiation-based decision support

At the centre of this use case is the development of an AI-supported multi-agent system that represents the key actors of the Austrian healthcare and social system through specialised agents. Each agent takes on the role of an institution or interest group and represents its goals, patterns of argumentation, scope for action and strategic interests.

The system should not only analyse information, but independently conduct discussions, debates and negotiations between the actors involved.

This creates a virtual negotiation space in which healthcare policy questions can be examined from different perspectives and possible solutions developed.

## Institutional AI agents

Each agent represents a relevant stakeholder in the Austrian healthcare system and independently develops positions based on data, historical decisions, public statements and institutional goals.

**Possible agents:**

1. Social insurance
2. Ministry of Health
3. Federal provinces
4. Medical chamber
5. Contract physicians
6. Private-practice physicians
7. Hospitals
8. Care-sector representatives
9. Patient representatives
10. Legislators
11. Ministry of Finance
12. Public health experts
13. Economic chamber, Chamber of Labour and Agricultural chamber
14. Industry (e.g. pharma)

**Each agent has:**

- its own objectives,
- defined interests,
- constraints,
- budget specifications,
- decision priorities,
- historical positions,
- institutional knowledge.

The agents should not simply deliver pre-produced answers, but argue depending on the situation, respond to counterarguments and adjust their position where necessary.

The agents' stance can be derived, for example, from the press archive or from news agency reports.

## Autonomous discussions and negotiations

A key feature of the system is the agents' ability to interact with one another independently.

Depending on the question, the agents can:

- discuss,
- debate,
- negotiate,
- develop counter-positions,
- form coalitions,
- seek compromises,
- work out alternatives,
- assess the impact of their proposals.

**Example question:**

> "How can healthcare spending be reduced by 10 % by 2035 without substantially worsening the quality of care?"

**Possible process:**

1. Each agent first develops its initial position.
2. The agents present their interests and arguments.
3. Other agents respond to them.
4. Points of conflict are identified.
5. Compromise proposals are worked out.
6. The proposals are assessed in terms of cost, acceptance and feasibility.
7. The agents gradually converge on a shared solution.

## Moderator agent

Optionally, a dedicated AI agent can take on the role of a neutral moderator.

This moderator agent:

- translates the user's question into a negotiation mandate,
- determines the relevant actors,
- defines the negotiation rules,
- steers the discussion,
- calls for justifications,
- detects contradictions,
- summarises interim results,
- documents points of consensus and conflict,
- ends the negotiation once a defined outcome is reached.

The moderator does not represent a position of its own, but ensures a transparent, structured and traceable negotiation process.

## Transparency and traceability as a central design principle

A key goal of this use case is that the agents' results do not appear as a "black box".

The end user must be able to trace at all times:

### Who represented which position?

The following should be made visible for each agent:

- original position
- key arguments
- data sources used
- strategic goals
- priorities

### Which discussions took place?

The system should provide a transparent negotiation history:

- arguments and counterarguments
- agreement and rejection
- points of conflict
- changes of opinion
- compromise proposals

This can take the form of, for example, a negotiation protocol or a chat view.

### Which interim results were achieved?

Interim results should be documented during the negotiation:

- topics with high agreement
- open conflict areas
- alternative solution paths
- failed proposals
- newly emerged options

### What did the agents agree on?

In the end, the system automatically produces:

- points of consensus
- majority positions
- minority positions
- remaining conflicts
- recommendations for action

## A negotiation result instead of a single answer

The actual output of the system should not just be an AI-generated answer.

The output consists of:

| # | Component | Guiding question |
|---|---|---|
| 1 | Summary of the initial question | Which question was examined? |
| 2 | Agents involved | Which institutions were involved? |
| 3 | Negotiation history | Which arguments were exchanged? |
| 4 | Conflict analysis | Where were the greatest differences of interest? |
| 5 | Compromise proposals | Which approaches were developed? |
| 6 | Consensus analysis | What were the agents able to agree on? |
| 7 | Open points of dispute | Which differences remain? |
| 8 | Impact | Which consequences are to be expected under the respective scenarios? |

## Game-theoretic negotiation mode

To increase realism, the institutional agents can apply game-theoretic strategies.

In doing so, the agents analyse:

- strategic advantages,
- negotiating power,
- coalition options,
- mutual dependencies,
- incentive systems,
- risks of cooperation or blockade.

This produces not just an aggregation of opinions, but a realistic simulation of political and institutional decision-making processes in the healthcare sector.

## Choosing a realistic data basis

The discussing agents can also argue on the basis of figures and facts. These arguments carry more weight, but must be substantiated in a robust way. The figures must not contradict one another and must be verified through tests or feedback loops. This can be done, for example, via a dedicated "expert" agent.

## Requirements

1. Institutions must not be represented by individual real-world persons. No statements by real persons may be quoted or depicted.
2. Make transparent how the AI agents' positions for the individual players come about. Positions come from media reports and press statements by the players — this must be made traceable.
3. Agents should learn how the partial results of negotiations turn out and take these into account in subsequent negotiation rounds.
4. Current events and information should be considered and weighted more strongly than historical information.

## Concrete application scenario: reducing waiting times for specialist appointments

### Starting situation

In several regions of Austria, waiting times for specialist appointments are rising continuously. At the same time, the social insurance institutions are under cost pressure, while physicians report increasing workload and staff shortages.

The following question is raised:

> "How can waiting times for specialist appointments be reduced by 20 % within five years without increasing healthcare spending by more than 5 %?"

### AI agents involved

Several institutional agents are activated to work on the question:

- Ministry of Health
- Social insurance
- Medical chamber
- Contract physicians
- Hospitals
- Care-sector representative
- Federal provinces
- Patient representative
- Ministry of Finance

Each agent has its own goals and evaluation criteria.

### Example interests

| Agent | Interests |
|---|---|
| Social insurance | Limit cost increases; promote efficient service delivery |
| Medical chamber | Preserve the attractiveness of the medical profession; ensure quality of care |
| Patient representative | Faster appointments; high quality of treatment |
| Federal provinces | Ensure regional care; guarantee political feasibility |
| Ministry of Finance | Maintain budget stability; limit additional spending |

### Phase 1: Position formation

Each agent first analyses the question independently.

For example:

- the medical chamber could demand more contract positions,
- the social insurance could rely on telemedicine and digital triage,
- the patient representative could call for longer opening hours,
- the Ministry of Finance could support investment only where impact is demonstrable.

These positions are documented together with the underlying arguments and sources.

### Phase 2: Discussion and debate

The agents discuss their proposals with one another.

**Example dialogue**

> **Medical chamber agent:** The main cause of waiting times is the shortage of specialists. Without additional contract positions, no sustainable improvement will be achieved.
>
> **Social insurance agent:** New positions create high ongoing costs. It should first be examined which services can be delivered via telemedicine.
>
> **Patient representative agent:** Digitalisation alone is not enough. Older people in particular continue to need in-person care.
>
> **Federal provinces agent:** In rural regions, mobile care units may be more efficient than additional locations.

### Phase 3: Negotiation

A structured negotiation then begins.

The moderator agent identifies:

**Points of consensus**

- Waiting times must be reduced.
- Regional differences must be taken into account.
- Digital offerings can make a contribution.

**Points of conflict**

- Number of additional contract positions
- Level of the necessary investment
- Balance between telemedicine and in-person care

The moderator asks the agents to develop compromise proposals.

### Phase 4: Finding a compromise

After several negotiation rounds, the following package of measures emerges:

**Agreed measures**

1. Expansion of telemedicine for selected services
2. Creation of additional contract positions in shortage regions
3. Introduction of digital specialist triage
4. Extended competencies for certain health professions
5. Monitoring of waiting times via a national dashboard

**Proposals not implemented**

- Nationwide cuts in remuneration
- Mandatory telemedicine for all patients

These proposals did not receive sufficient support from the agents.

### Phase 5: Transparent presentation of results

The end user now receives the entire decision-making process along with the necessary background knowledge.

**Dashboard components**

- **Actors involved**
  - Which agents were involved?
  - Which goals do the respective agents pursue, and which positions did they adopt?
- **Negotiation history**
  - Which arguments were put forward?
  - Which counterarguments were there?
  - Which positions changed?
- **Consensus analysis**

  For each topic, the approvals, arguments and positions per actor should be shown, including how they change over the course of the negotiation.

- **Open conflicts**
  - Financing of new positions
  - Distribution of resources between urban and rural areas

### Expected impact

Simulation results:

- Waiting time reduction: 22 %
- Budget increase: 4.3 %
- Greater care security in rural regions
- Medium feasibility within 3 to 5 years

### Benefits of the scenario

This example shows the central added value of the multi-agent approach: the AI does not deliver a single answer, but simulates a realistic healthcare policy decision-making process. Users see transparently

- which institution represented which interests,
- which arguments were exchanged,
- where conflicts arose,
- which compromises were found,
- and why the final recommendation came about.

This creates a digital negotiation and consensus space for complex questions in the Austrian healthcare system. The approach can be transferred to topics such as remuneration negotiations, hospital planning, care reforms, primary care units, vaccination strategies or the financing of new health services.

## Data sources

- Press archive of the umbrella association
- Legal foundations: SOZDOK

## Evaluation criteria for the expert jury

The HealthPolicy Simulator should realistically represent different institutional perspectives on healthcare policy questions. The AI agents should take the respective interests, goals and framework conditions of the institutions they represent into account in a traceable way and base their positions on suitable information sources.

The focus is on a dynamic discussion in which the agents react to one another, pick up counterarguments and bring out existing goal conflicts. The aim is to examine different approaches, weigh their advantages and disadvantages and develop comprehensible compromise proposals. Alternative scenarios, possible impacts and remaining conflicts should also be taken into account.

A key element is the transparency of the entire decision-making process. The sources used, key arguments, assumptions and changes of position should be presented in a traceable way. Results should be prepared in an understandable form and deliver concrete bases for decisions, without obscuring uncertainties or artificially forcing a consensus.

The negotiation, the arguments exchanged within it, and the interests and goals assessed in relation to the questions should be presented in a visually understandable way. Changes in positions during the negotiation should likewise be visualised.

The solution should be demonstrated using a working prototype. Alongside subject-matter quality, independent technical implementation, the interplay of the AI agents and the use of suitable data and knowledge sources also count. Also consider how your solution could be developed beyond the prototype and made usable for practical application.

## Evaluation criteria for the final jury

_(Still open.)_
