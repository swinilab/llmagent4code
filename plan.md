
[] gen app: 
	[x] chatdev - qwen3.5 (v1)
		. latest.md
	[] chatdev (v2) @manh
	[x] claude
	[] codex @congnv


[] 2. functional test
	a. [] check domain constraint fields - validate testcases - vba/ep 
		@duc @lam
	b. use: chatdev (v1)
	[] log testcase execution: request/ response
		@manh
	[] check test log -> verify test result
		@duc @lam
	[] hiệu chỉnh functional check   
		@manh
	c. [] test generated apps @manh
		[] chatdev
		[] claude
		[] codex

[] 3. validate qa: static
	[]. ind-score: qa/ tactic @duc @hai
		. score1(tactic, function)
			. nfr-trace-> absent (0)/present (1)
			[] . check lib code template: from (doc) -- code gen: similarity score 
		. score2(tactic, function-in-trace) = % sum(score1)/num-functions
		. score3(qa, tacticset) = avg(score2-by-qa)
	[] test generated apps @duc
		[] chatdev
		[] claude
		[] codex

[] 4. validate conflicting qa
	. conf-score: 
		. conf-tacticset = {(x, y)} 
		. score_trace(x, y, f) = 1/(score1(x, f) + score1(y, f)) when f1=f2=f and where score1(x,f)+score1(y,f) != 0  (in (0, 1])
				         
		. score_trace(x, y, f1, f2, trace(f1, f2)=true) = (score_func(x,y,f1) + score_func(x,y,f2))/ length(path(f1, f2)) (in (0, 2]/n)

		. conf_score(conf-tacticset) = avg(score_trace(x,y,f1,f2)) where:
			. foreach tactic-pair (x, y)
				. foreach function f1 implement tactic x
					. foreach function f2 implement tactic y: trace(f1, f2) = true
						score_trace(x,y,f1,f2)
	
	> output table: - validate using static qa					
	
	- mutliple copy of data (cache) <-> exception detection 
	- ..

[] writing: 
	[] pipeline: 
