I built a simulator of AI agents playing humans to look at organizational dynamics from a different angle. I was interested in questions like how under/overstaffing affect productivity, how different performance review change incentives, and lately, how we should rethink about the optimal human organization setup with the introduction of AI agents. 

The idea came from a recent Waymo offsite. I participated in one of those team building games: given a pile of parts, such as straws and cardboards, each team competed to build a structure, subject to some rules .

To adapt that to the digital world, in the simulator, I gave a team of AI agents different personas and skills. Together they need to succeed at a virtual domino task. They had to discuss and agree on a common vision (the domino layout), execute efficiently (lay down the bricks) and collaborate (make ends of domino segments built by different agents meet). In the end, with a push, the fallen pieces should form a shape that can be recognized by the judge. 

Here are the results from the experiment on staffing size. A solo team couldn’t succeed due to the sheer volume of work. But a team of 10 talked 60% more than 4 and each person laid 33% fewer dominoes on average. A lot of time was spent on coordination. And the final output was neither faster nor better. The negatives of overstaffing were exacerbated when the team was weaker (played by Haiku instead of Sonnet agents). 

Does that resonate with your experience in big corporations vs startups?

Obviously, caveats apply. These are AI agents, not people, and a ten-minute domino game isn't a product launch. What the simulator is good at is making mechanisms visible and tunable. Whether those mechanisms match your own teams is for you to judge

Comment to share what experiments you want to see! I got a few still running (by Claude Code). 

https://github.com/lilipads/org-sim