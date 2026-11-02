from pathlib import Path
import json,re,copy,subprocess,sys
P=Path(__file__).parent/'lessons'
def S(title,sec,lines,a,b,c,d,why):return dict(title=title,section=sec,code_lines=lines,input=a,action=b,output=c,state=d,why=why,failure=False)
def save(n,after,bridge,coverage,qs,steps,failure,overrides=None,changes=None):
 f=next(P.glob(f'{n:02}-*.json'));l=json.loads(f.read_text());heads=re.findall(r'^## (.+)$',l['body'],re.M)
 if changes:
  for a,b in changes:l['body']=l['body'].replace(a,b)
 l['alignment']=dict(case_title=l['lab']['title'],insert_after=heads[after],bridge=bridge,coverage=coverage,question_sections=[heads[i] for i in qs])
 for i,s in enumerate(steps):s['node']=i;s['section']=heads[s['section']]
 if isinstance(failure,tuple):
  end,updates=failure;bad=copy.deepcopy(steps[:end+1])
  for index,props in updates.items():bad[index].update(props)
 else:
  bad=failure
  for i,s in enumerate(bad):s['node']=min(i,len(steps)-1);s['section']=heads[s['section']]
 bad[-1]['failure']=True
 cases=[dict(id='normal',label='正常：逐行对照参考程序',basis='本分支使用下方参考程序的原始输入；步骤只解释这份程序实际实现的机制，最终输出与实验预期一致。',steps=steps),dict(id='failure',label='边界变式：对照同一份程序',basis='边界分支沿用同一实验。若列出替换行，代码片段展示替换后的变式；下方完整参考程序仍保留正常版本。',steps=bad,code_overrides=overrides or {})]
 l['diagram']=dict(nodes=[s['title'] for s in steps],caption='本图只展开《'+l['lab']['title']+'》的代码机制；每一帧与下方程序、当前正文概念对应。',walkthrough=dict(scenario=l['lab']['task'],cases=cases))
 f.write_text(json.dumps(l,ensure_ascii=False,indent=2))

save(7,3,'前面用2025版400元与2026版500元说明：语义相关并不保证制度适用。现在把这件事缩成同一份可运行程序，不再另换文档ID或城市。`docs`里只有三条记录：`old`是2025年住宿400元，`new`是2026年住宿500元，`food`是2026年餐饮100元。用户问题固定为`query={上海,住宿,标准}`，本例已假定用户是普通员工。\n\n接下来先看第7行如何筛出2026年记录，再看第8行怎样给两条候选排序：`new`与问题重合3个词，`food`只重合上海1个词，所以`ranked[0]`必须是`new`。第10行断言检查选对记录，最后一行才读取`limit`和`id`生成可手算的输出。因此演示、断言和预期输出说的都是同一个500元。\n\n请先预测删除年份过滤会发生什么，再切换边界分支。旧版和新版都命中3个词，稳定排序会保留旧版靠前的位置，断言因此失败。你看到的不是另一套RAG，而是刚才“适用性先于相似度”的具体后果。看完演示后紧接着运行下面这11行代码。','程序只实现年份过滤、词项重合排序与字符串答案。没有PDF解析、角色ACL、真实Embedding、向量数据库或LLM生成；这些是正文讲的完整系统组件，不能当作本程序已实现。',[1,3,2,4],[
S('读取三条制度',1,[1,5],'docs包含old、new、food','保留各自tokens、year、limit，不把向量当原文。','old=400/2025；new=500/2026；food=100/2026','len(docs)=3','检索表示和最终可读取事实同时存在，后面才能引用记录ID。'),
S('保留原始问题',2,[6,6],'用户问上海住宿标准','将查询表示为三个词，便于手算匹配。','query={上海,住宿,标准}','query_terms=3','这里用词集合代替真实Embedding，只观察检索数据流。'),
S('先过滤年份',3,[7,7],'当前制度年份2026','只保留year等于2026的记录。','allowed=[new,food]','excluded=[old]','先选适用资料，避免旧制度仅因相似而进入答案。'),
S('对候选排序',2,[8,8],'allowed中的new与food','分别计算查询词交集大小：new为3，food为1。','ranked=[new,food]','scores={new:3,food:1}','排序解决相关性，上一帧的过滤解决适用性，两者职责不同。'),
S('验证选中记录',3,[9,10],'ranked[0]是new','赋给evidence并执行ID断言。','evidence.id=new，断言通过','evidence.limit=500','断言让错误过滤能被看见，不靠自然语言答案是否顺眼判断。'),
S('输出金额和引用',2,[11,11],'evidence.limit=500；id=new','从同一原记录读取金额与出处。','答案：500元/晚；引用：new','stdout与下方预期输出完全相同','答案不是凭模型记忆补出的；每个值都能追到选中的记录。')],(4,{2:dict(action='变式删除年份过滤，把全部docs交给排序。',output='allowed=[old,new,food]',state='excluded=[]'),3:dict(input='old与new都命中3词，food命中1词',action='稳定排序保留old在new前的原顺序。',output='ranked=[old,new,food]',state='scores={old:3,new:3,food:1}'),4:dict(input='evidence=old',action='第10行仍要求ID为new，检查发现旧版被选中。',output='AssertionError；第11行未执行',state='answer_sent=false; selected_id=old',why='这正是正文所说“旧制度排名第一也不能直接使用”，错误发生在过滤层。')}),{'7':'allowed = list(docs)'})

save(8,3,'正文刚手算了A与B的RRF分数，现在就用完全相同的A、B、C与两份排名运行程序。这里不再演示PDF解析、向量召回或重排器，只研究中间这一个问题：两条已得到的排名怎样合成一条？第一路是`[A,B,C]`，第二路是`[B,C,A]`，常数`c=60`。\n\n`rrf`先创建空分数表，再按每一路排名累加`1/(60+rank)`。`rank`从1开始，因此第一名贡献1/61。第6行的`dict.fromkeys`先消除同一路重复ID；同一文档跨两路出现可以累加，同一路把自己重复列两遍却不能多拿一票。两路完成后，第8行按负分数升序，也就是实际分数降序排列；文档ID作为同分规则。\n\n下面演示会把B=0.032522、A=0.032266、C=0.032002与最后打印结果接在一起。边界分支故意让第一路重复A，并去掉去重操作，观察A如何被刷到第一。这不是新的系统架构，而是检查RRF实现为什么需要一个具体的数据不变量。演示末步看到的三行结果，就是紧接着程序的预期输出。','本实验只实现排名融合。两路排名已手工给定，不运行BM25、Embedding、ANN、Cross-Encoder或真实检索器。',[0,2,1,2],[
S('接收同一组排名',3,[10,10],'两路：[A,B,C]与[B,C,A]','调用rrf，默认c=60。','待融合的3个唯一文档','lists=[[A,B,C],[B,C,A]]','正文公式中的rank来自各路排序，不是原始相似度分数。'),
S('创建分数表',3,[3,4],'c=60，尚未累计','用defaultdict(float)为首次出现文档从0计分。','scores={}，缺失初值为0','scores[A]=0（读取默认值时）','缺席某路没有贡献，不应伪造一个末位分数。'),
S('先按一路去重',2,[5,6],'第一路[A,B,C]','dict.fromkeys保持首次顺序并去重；枚举从1开始。','(A,1),(B,2),(C,3)','first_route_ranks={A:1,B:2,C:3}','同一路的重复记录不代表额外证据，不能刷票。'),
S('累加两路贡献',3,[6,7],'每个doc及其在当前路的rank','B加1/62与1/61，A加1/61与1/63，C加1/63与1/62。','B≈.032522；A≈.032266；C≈.032002','scores完成两路累加','这一帧就是正文手算式子的循环实现。'),
S('稳定排序并断言',3,[8,11],'完成的分数表','按(-score,doc_id)排序，并检查第一名确为B。','result=[B,A,C]','result[0][0]=B','同分规则保证可重复；高排名仍不是文档事实正确的证明。'),
S('打印融合分数',3,[12,13],'result包含文档与浮点分数','格式化为6位小数输出。','B 0.032522\nA 0.032266\nC 0.032002','stdout与实验预期一致','读者应能把每个打印值还原到两次排名贡献。')],(4,{0:dict(input='第一路变为[A,A,B,C]，第二路仍[B,C,A]',output='本分支测试重复文档',state='duplicate_in_one_route=A'),2:dict(input='第一路[A,A,B,C]',action='变式第6行直接枚举ranking，漏掉去重。',output='A在第1、2名分别获得贡献',state='deduplicated=false'),3:dict(action='重复A被计两票，第二路再贡献一次。',output='A≈.048395，高于B≈.032266',state='ranked_first=A',why='不是A相关性提高了，而是同一路重复记录被错误当成独立贡献。'),4:dict(input='result第一名是A',action='第11行仍断言B应第一，暴露去重错误。',output='AssertionError，尚未打印结果',state='RRF去重不变量被破坏',why='用同一组基线排名及一处重复，解释为何融合前必须按文档ID去重。')}),{'6':'        for rank, doc in enumerate(ranking, 1):','10':'result = rrf([["A","A","B","C"],["B","C","A"]])'})

save(9,2,'刚才的已解例固定相关证据为`{A,B}`，返回列表为`[X,A,Y]`。下面不会再插入新的上线、灰度或引用案例，而是直接展开这份指标函数：前3条只有A相关，因此Recall@3是1/2；第一条相关结果在第2位，所以单题RR@3也是1/2。两项数字碰巧相同，但分母来源完全不同。\n\n演示与代码都先计算这组结果，再计算`[A,B,X]`：A、B都被找到，Recall变成1；第一条就是相关结果，RR也变成1。你可以对照第3行集合交集和第4行第一次命中的枚举位置，理解“覆盖了多少证据”和“最早多久遇见证据”的区别。MRR是多题RR取平均，这里函数返回的是单题RR。\n\n最后用程序已有的空相关集合断言解释边界：`relevant=set()`时，Recall分母为零，所以返回`None`，不能当作100%召回。这条分支是数学定义处理，并非系统坏了。看完演示就运行同一函数，再按下方变式把列表改为`[A,X,Y]`，亲自确认Recall保持0.5而RR升至1。这样正文、演示、代码和习题都围绕同一个集合与排名展开。','只手算并验证Recall@K和单题RR@K。没有调用LLM裁判、执行全量RAG或真实灰度发布；这些属于本章其余概念。',[1,2,4,5],[
S('固定标注和排名',2,[7,7],'ranking=[X,A,Y]，relevant={A,B}，k=3','把同一组数据传给metrics。','总共需要找回2条相关证据','gold_count=2','先固定相关集合，指标才有明确分母。'),
S('取前K并算覆盖',1,[2,3],'top=[X,A,Y]','去重后与{A,B}求交，只得到A。','recall=1/2=0.5','found_relevant={A}','Recall的分母是应找回证据数，不是返回条数。'),
S('找首条相关位置',1,[4,5],'依次查看X、A、Y','第2位A首次相关，取倒数1/2。','rr=0.5','first_relevant_rank=2','RR关心首条位置，不关心B有没有同时出现。'),
S('输出第一组结果',2,[8,9],'recall=.5，rr=.5','断言并格式化结果。','Recall@3=0.50, RR@3=0.50','first_case_pass=true','数值相同是这份输入的巧合，含义并不相同。'),
S('换成完整证据排名',2,[10,11],'ranking=[A,B,X]，gold仍{A,B}','重新算交集及首条相关位置。','Recall@3=1.00, RR@3=1.00','second_case=(1.0,1.0)','同一函数换输入即可验证指标变化，不需另一个业务故事。'),
S('核对无相关集合边界',1,[12,12],'metrics([X],set(),1)','调用已有边界用例，检查Recall返回None。','断言通过；空gold不被伪造为满分','empty_gold_recall=None','无答案任务和缺少相关性标注应另行评估，不能强塞此分母。')],[
S('选择程序已有边界',1,[12,12],'ranking=[X]，relevant=set()，k=1','进入metrics函数，沿同一代码推演。','没有可定义的相关性分母','len(relevant)=0','这不是把未答题判错，而是检查指标适用条件。'),
S('仍可截断列表',1,[2,2],'ranking=[X]，k=1','top=ranking[:k]。','top=[X]','top_count=1','取前K本身不要求gold非空。'),
S('避免除零',1,[3,3],'relevant为空','条件表达式走else None，不执行除法。','recall=None','recall_undefined=true','None明确表示此指标不适用，不代表检索成功或失败。'),
S('计算无命中的RR',1,[4,5],'X不在空gold中','生成器没有首次命中，next使用默认值0。','返回(None,0)','rr=0','RR的默认值与Recall的未定义值各有语义。'),
S('边界断言通过',1,[12,12],'metrics结果(None,0)','第12行检查第0项为None，测试成功。','程序不报错；按任务另选无答案指标','empty_gold_test=pass','本边界分支到此结束，不把未定义的Recall解释成0或1。')])

save(10,2,'正文的集合例子就是这份程序：张老师的学生是`{A,B}`，项目成员是`{B,C}`，答案应为交集`{B}`。为把机制看清楚，实验把两份资料放在` sources`字典里，取代真实检索工具；`state`保存已得到的`facts`、尝试次数`attempts`和检索轨迹`trace`。这些名字会原样出现在演示和代码里，不再换成calls_used等另一套状态。\n\n循环先处理`students`，再处理`project`。第4行在行动前查预算，第6行递增次数，第7行把本次结果写进facts。第一次完成后只有students，第二次完成后两个字段才齐全。第10行检查字段覆盖，第11行求交集，最后打印`answer: B`。你可以在每一步同时看上方状态快照和下方对应代码，不需要想象它们如何对应。\n\n边界分支只改第4行的上限，从2改成1。于是第一份资料取得后，第二次循环会直接break，facts里没有project；同一第10行条件不成立，进入第15行打印`insufficient evidence`。这正是正文“达到上限不是完成”的具体例子。实验没有自主LLM规划器，所以它训练的是证据覆盖与有界循环，不是宣称复现了自主研究Agent。','sources为人工资料字典，子问题顺序写死。实验只验证状态、预算和集合覆盖，不执行真实检索、LLM路由、图数据库或生成质量裁判。',[3,0,2,3],[
S('准备同一份资料和状态',1,[1,2],'students={A,B}；project={B,C}','创建facts空字典、attempts=0和trace空列表。','资料还没写入任务状态','facts={}; attempts=0; trace=[]','资料存在于sources不代表系统已完成获取；facts记录本次确实得到什么。'),
S('首次预算检查',3,[3,5],'need=students；attempts=0','0>=2为假，允许执行本轮。','可以获取学生名单','attempts=0; next_need=students','在动作前检查，才能保证不会先超额执行再统计。'),
S('写入第一份证据',2,[6,9],'sources[students]={A,B}','attempts加1，将资料写入facts，再追加trace。','step1: retrieve students','facts={students:{A,B}}; attempts=1; trace=[students]','有一份相关资料还不够，问题仍需要项目成员集合。'),
S('写入第二份证据',2,[3,9],'need=project；attempts=1','1>=2为假，第二轮写入project并记录轨迹。','step2: retrieve project','facts={students:{A,B},project:{B,C}}; attempts=2','只有这一步后，交集所需的两个输入才都在facts里。'),
S('检查字段是否齐全',2,[10,10],'facts有students和project两个键','判断所需键集合是否是facts.keys的子集。','条件为真，允许进入求交集分支','required_keys_present=true','非空不等于充分；此处明确定义了充分的两个字段。'),
S('求交集并输出',2,[11,16],'学生{A,B}与项目{B,C}','求交、排序、打印，并检查结果和次数。','answer: B','answer=[B]; attempts=2','同一个B既在正文的已解例里，也在程序断言和输出里。')],(4,{1:dict(input='need=students；attempts=0；本变式上限1',action='0>=1为假，允许唯一一次获取。',output='本轮可继续，之后没有第二次额度',state='attempts=0; limit=1'),3:dict(input='第二次循环need=project；attempts=1',action='变式第4行检查1>=1为真，break，未写入project。',output='不执行第二次retrieve',state='facts={students:{A,B}}; attempts=1; trace=[students]'),4:dict(input='facts只有students，没有project',action='第10行条件为假，进入else，第15行说明资料不足。',output='insufficient evidence',state='answer_not_computed=true; attempts=1',why='这正对应正文的预算边界：循环可以结束，但不能假装第二份证据已经到手。',code_lines=[10,16])}),{'4':'    if state["attempts"] >= 1:'})

save(11,2,'这一节讨论CRAG式检索纠偏，下面的小实验只把“评估信号怎样变成下一动作”写成可运行规则。`scores`是已经给定的教学分数，不是本程序从文档里算出来的。固定四组输入依次为`[0.9,0.85]`、`[0.1,0.2]`、`[0.9,0.2]`和`[]`，因此演示和程序都只围绕这四组数，绝不突然出现内部API返回500元等未实现的数据。\n\n先看第2行：分数全不低于0.8且列表非空，返回`refine`。否则第4行判断空列表或所有结果都很弱，返回`fallback`。剩余混合信号返回`combine`。你看到的三个词只是路由结果；真正精炼文档、联网搜索、再生成答案还没有执行。区分“决定去做什么”和“已经做完什么”，就是读Agent代码时必须保留的边界。\n\n最后再看空列表：第4行的`not scores or ...`通过短路避免对空列表求max。边界演示故意删除`not scores or`，前三组仍可得到结果，第四组才报错。这样你既能把CRAG的纠偏位置与真实代码对应，也能看到一个明确的Python控制流边界。本课其余Self-RAG、Adaptive和FLARE继续作为机制对比，不伪装成这个规则函数已经实现。','仅模拟检索后路由；没有训练评分模型、反思token、问题复杂度分类器或FLARE检索，也不执行Web搜索。0.8/0.3为人为示例阈值。',[1,2,3,4],[
S('查看规则与四组分数',2,[1,9],'四个列表按代码第8行顺序给定','调用decide，观察分数如何触发分支。','函数只返回动作名','inputs=[[.9,.85],[.1,.2],[.9,.2],[]]','先将“信号”和“执行动作”分开，避免把路由当已经补到证据。'),
S('高分走精炼',2,[2,3],'scores=[0.9,0.85]','两项均>=0.8且列表非空。','refine','all_high=true','这对应评估可信检索结果后保留并精炼的方向。'),
S('低分走补救',2,[4,5],'scores=[0.1,0.2]','非空且max=0.2<0.3。','fallback','max_score=.2','判断出需要兜底，不代表外部源一定有答案。'),
S('混合结果走组合',2,[2,6],'scores=[0.9,0.2]','不满足全高，也不是全低，进入最后返回。','combine','some_useful=true','保留有用部分并补缺，而不是仅看均值全部丢弃。'),
S('空列表也走补救',2,[2,5],'scores=[]','第2行因空列表不返回；第4行not scores为真，短路。','fallback','max_on_empty_not_evaluated=true','空列表的控制流保护是一行真实代码，不是模型反思。'),
S('输出并核对已有断言',2,[8,11],'四次调用完成','按顺序输出，并检查混合与空列表两个边界。','refine\nfallback\ncombine\nfallback','assertions=pass','这四行正是紧接着实验的预期输出。')],(4,{4:dict(input='scores=[]，变式删除空列表短路保护',action='第4行直接求max([])，触发ValueError。',output='ValueError: max() arg is an empty sequence',state='first_three_outputs=[refine,fallback,combine]; fourth_result=error',why='失败来自Python空集合操作，不应解释成CRAG判断资料不存在。')}),{'4':'    if max(scores) < 0.3:'})

save(12,4,'刚才的已解例给出张老师→小李→项目X→研究所Y这条关系链。下面三条`edges`就是这三份资料，不再添加新的实体、社区层级或抽取器。每条记录是`(起点,关系,终点,来源)`：例如第二条把小李、参与、项目X和doc2放在一起。程序用集合与列表推导式把这些关系连接起来，让你手工核对“哪一步保留谁”。\n\n第6行按指导关系取终点b，得到学生小李；第7行找到资助方为研究所Y的项目，得到项目X；第8行只保留同时满足“人属于学生集合、项目属于资助项目集合”的参与记录。因此`hits`只能是`[(小李,项目X,doc2)]`。最后的输出把路径和三个来源展示出来，和本段的图相互对应。\n\n失败分支只把第6行的b错写成a。代码仍然能运行，但students会变成张老师，后面的参与连接得到空列表，原断言暴露错误。这让正文“保留关系方向”成为可观察的程序行为。这个小实验不是完整GraphRAG构建器：实体与关系已经人工标好，未调用LLM、Leiden或摘要。社区与离线索引在前面理论段解释；此处只拿其中的关系连接机制做实作。','人工给定三元组，只验证方向、集合连接和来源关联。没有运行实体抽取、消歧模型、社区检测或社区报告生成。',[2,4,0,5],[
S('读入三条带来源的边',4,[1,5],'doc1指导、doc2参与、doc3资助方','按同一四元组格式保存起点、谓词、终点、来源。','edges共有3条','sources=[doc1,doc2,doc3]','来源跟随关系保存，答案才能回查原文。'),
S('取指导关系的终点',4,[6,6],'张老师—指导→小李','筛a=张老师、r=指导后取b。','students={小李}','students={小李}','关系方向决定取a还是b，不是任意相邻实体都叫学生。'),
S('取Y资助的项目',4,[7,7],'项目X—资助方→研究所Y','筛r=资助方、b=研究所Y后取a。','funded={项目X}','funded={项目X}','这次要的是项目，故取起点a；与上一帧取b的原因不同。'),
S('连接参与关系',4,[8,8],'学生{小李}，项目{项目X}','参与边需同时满足a在students且b在funded。','hits=[(小李,项目X,doc2)]','matched_participation=1','三个条件连接起来，才回答“谁参与Y资助的项目”。'),
S('校验唯一匹配',4,[9,9],'hits包含一个带来源的参与记录','对照预先可手算的期望值。','断言通过','expected_hit=(小李,项目X,doc2)','断言检查连接实现，不能代替真实抽取数据的真实性审核。'),
S('打印同一条路径',4,[10,11],'已核验的匹配及人工给定边','显示路径与三份资料来源。','小李 → 项目X → 研究所Y\n证据：doc1, doc2, doc3','stdout与预期一致','路径、前面的正文已解例和这份程序指向相同的人与项目。')],(4,{1:dict(action='变式第6行误取a，而不是关系终点b。',output='students={张老师}',state='students={张老师}',why='把导师当学生，是取错三元组字段造成的方向错误。'),3:dict(input='students={张老师}，funded={项目X}',action='没有张老师参与项目X的边，小李也不在错误学生集合。',output='hits=[]',state='matched_participation=0'),4:dict(input='hits为空，但基线期望小李',action='第9行断言失败，提醒回查第6行的方向。',output='AssertionError；尚未打印路径',state='join_valid=false',why='不能把程序连错导致的空结果说成“小李没有参与”，先核对连接条件。')}),{'6':'students = {a for a,r,b,s in edges if a == "张老师" and r == "指导"}'})

save(13,2,'这一节的“不能简单数关键词”会直接落到下面两份`reports`。第一份是`[(A,检索),(B,多Agent)]`，第二份是`[(A,检索),(C,检索)]`。A被两份报告重复提到，B只出现一次，C只出现一次；最终真实项目有A、B、C三个，其中检索方向的项目应是A、C两项，而不是把A的两次转述计成两个项目。\n\n本例把Map输出人工写好，程序只执行Reduce。第7—9行遍历每份报告和每个项目主题对，用主题作为字典键，用项目ID放进集合。第一份处理后，检索对应{A}、多Agent对应{B}；第二份再加入A时集合不变，加入C后才变成{A,C}。第10行明确检查这个不变量，最后排序输出，保证显示顺序稳定。\n\n演示会逐次展示同一个`merged`字典怎样改变；紧接的代码就是同样的两个输入列表。边界分支故意把项目身份改成“项目ID＋报告编号”，A在两份报告中就变成两个不同键，断言会暴露错误。这不是另一种Local Search案例，而是Global聚合里一个很小但关键的去重机制。完整LLM Map和社区检索尚未运行，请把这份程序的能力边界和正文全景分开。','只执行人工Map结果的Reduce与稳定输出，不运行实体定位、Local Search、社区生成或真实LLM Map。',[3,2,0,1],[
S('读取两份相同示例报告',2,[1,5],'r1有A/检索、B/多Agent；r2有A/检索、C/检索','把Map结果当已给定输入。','4次提及，3个真实项目','mentions=4; project_ids={A,B,C}','出现次数和真实实体数从一开始就不同。'),
S('初始化聚合字典',1,[6,6],'还没有处理任何项目主题对','创建空merged。','merged={}','themes=[]','Reduce必须保存实体身份，而非只累计文字频率。'),
S('处理第一份报告',2,[7,9],'(A,检索)、(B,多Agent)','按theme建立集合并add(project)。','merged={检索:{A},多Agent:{B}}','processed_reports=1','每个主题下保存稳定项目ID，为去重建立依据。'),
S('处理第二份报告',2,[7,9],'(A,检索)、(C,检索)','再次加入A集合不变；加入C增加一个项目。','merged={检索:{A,C},多Agent:{B}}','processed_reports=2; retrieval_projects=2','这一步才体现“重复转述不增加独立项目”的机制。'),
S('校验聚合不变量',2,[10,10],'检索主题集合已经形成','检查结果恰为{A,C}。','断言通过','merged[检索]=={A,C}','若用来源位置当身份，这个断言会及时抓到重复计数。'),
S('稳定打印主题与项目',1,[11,12],'两个主题与对应集合','主题排序；各集合内部也排序。','多Agent B\n检索 A,C','stdout与预期一致','同一结果可回到两份reports中的原始项目，而不是新编实体。')],(4,{2:dict(action='变式将项目ID附上报告编号，错误地把来源位置变成身份。',output='merged={检索:{A-report1},多Agent:{B-report1}}',state='identity=project_plus_report'),3:dict(action='同一A在第二份被写成A-report2，集合无法把两次转述合并。',output='检索:{A-report1,A-report2,C-report2}',state='retrieval_count=3 (错误，应为2)',why='不同来源是同一实体的证据，不应改写实体ID。'),4:dict(input='检索集合含带报告后缀的三项',action='第10行仍期望稳定实体集合{A,C}，断言失败。',output='AssertionError；不输出错误汇总',state='entity_deduplication=fail',why='这就是正文重复计数问题在同一份Reduce程序里的具体反例。')}),{'9':'        merged.setdefault(theme, set()).add(project + "-report" + str(reports.index(report)+1))'},changes=[('报告一说项目A研究检索并存在延迟问题，报告二说项目B研究多Agent并存在评测问题，报告三也提到项目A的检索方向。','本例报告一给出项目A属于检索方向、项目B属于多Agent方向；报告二重复提到A，并补充项目C也属于检索方向。这正是下方程序的两份reports输入。')])

save(14,2,'本课前面列了HyDE、RAPTOR和多模态三条不同改进路线。为了不把它们混成一个程序，这里只对RAPTOR式“多层节点与原文回溯”做一个最小机制实验：人工给定三个叶子a、b、c，以及两个父主题“检索质量”和“工具治理”。a的原文是检索延迟高，b是检索召回不足，c是工具需要权限。它们就是紧接着代码里的`leaves`与`parents`，不是另一套假想文档案例。\n\n用户的查询只含“检索”。第4行在父主题名上匹配，命中“检索质量”；第5行沿parents把它展开成叶子ID`[a,b]`。第8行再用这些ID回leaves取出真正文字。这样能清楚区分两个动作：高层主题帮你缩小范围，叶子保留具体证据。最后的断言检查回溯结果确为a、b。\n\n边界分支故意跳过“父主题→叶子ID”映射，直接把“检索质量”拿去leaves查。程序会在第8行KeyError，因为父节点标题不是叶子键。这正对应正文要求保留父子来源关系，不能只检索到一个高层概括就假设已拿到原始细节。看完这个例子后再比较HyDE的检索探针和多模态页面路线；它们的原理有讲解，但这份小程序没有实现那些模型。','人工指定层级与关键词匹配，不运行RAPTOR真实聚类、LLM摘要、Embedding、HyDE生成或视觉解析。',[1,2,4,3],[
S('建立同一组父子资料',2,[1,2],'leaves:a延迟高、b召回不足、c工具权限','parents把检索质量关联a/b，把工具治理关联c。','可回溯的父子ID映射','parents[检索质量]=[a,b]','父主题是检索入口，叶子ID才是回原文的键。'),
S('保留查询词',0,[3,3],'query=检索','本例只做字符串主题匹配，不调用语义模型。','待匹配父主题','query=检索','先识别实验确实运行什么，避免把字符串查找当Embedding效果。'),
S('命中高层主题',2,[4,4],'父主题检索质量、工具治理','只有检索质量包含查询词。','hits=[检索质量]','matched_parents=1','命中高层只说明方向相关，尚未取回细节。'),
S('展开成叶子ID',2,[5,5],'hits包含检索质量','通过parents查出该主题对应的子节点。','ids=[a,b]','leaf_ids=[a,b]','显式的父子映射把摘要入口与原文证据连接起来。'),
S('读取并打印叶子原文',2,[6,8],'ids=[a,b]','先输出summary，再逐个读取leaves[child]。','summary: 检索质量\na 检索延迟高\nb 检索召回不足','retrieved_texts=2','真正帮助回答细节的是叶子内容，不能只复述主题名。'),
S('校验回溯结果',2,[9,9],'最终叶子ID列表','检查恰为[a,b]，c没有被误带入。','断言通过','ids==[a,b]','正文的多粒度思路在这里缩成可验证的来源回溯。')],(4,{3:dict(action='变式直接把父主题标题作为ids，跳过parents映射。',output='ids=[检索质量]',state='ids_are_leaf_keys=false',why='标题可读不等于它就是原文存储键，层级间必须显式映射。'),4:dict(input='child=检索质量，但leaves只有a、b、c',action='第8行执行leaves[child]，找不到该键。',output='先打印summary: 检索质量，然后KeyError',state='leaf_lookup=failed',why='失败发生在缺少父子映射，不是原文没有相关细节。')}),{'5':'ids = list(hits)'})

# Real execution verifies every baseline and all changed-input boundary programs.
for f in sorted(P.glob('*.json')):
 l=json.loads(f.read_text())
 if not 7<=int(l['id'])<=14:continue
 base=subprocess.run([sys.executable,'-c',l['lab']['code']],capture_output=True,text=True,timeout=10)
 assert base.returncode==0 and base.stdout==l['lab']['expected'],(f.name,base.stderr)
 for case in l['diagram']['walkthrough']['cases']:
  edits=case.get('code_overrides',{})
  if not edits:continue
  lines=l['lab']['code'].splitlines()
  for num,line in edits.items():lines[int(num)-1]=line
  r=subprocess.run([sys.executable,'-c','\n'.join(lines)+'\n'],capture_output=True,text=True,timeout=10)
  if l['id']=='10':
   assert r.returncode==0 and r.stdout=='step1: retrieve students\ninsufficient evidence\n',(f.name,r.stdout,r.stderr)
  else:
   assert r.returncode!=0,(f.name,'expected boundary guard to catch introduced fault')
  case['verified_result']=dict(returncode=r.returncode,stdout=r.stdout,exception=r.stderr.strip().splitlines()[-1] if r.stderr.strip() else None)
 f.write_text(json.dumps(l,ensure_ascii=False,indent=2))
print('07-14 aligned; baseline outputs and boundary overrides executed')
