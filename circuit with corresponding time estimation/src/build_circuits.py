"""Qiskit circuit atlas with PAPER fault-tolerant timing, not backend gate timings.

Run: python build_circuits.py --output .
The drawing examples and resource-estimation inputs are deliberately separate.
"""
from pathlib import Path
import argparse, base64, csv, html, json, math, os
os.environ.setdefault('MPLBACKEND', 'Agg')
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from qiskit import QuantumCircuit, QuantumRegister, qpy
from qiskit.circuit import Gate, Parameter
from qiskit.circuit.library import PhaseGate
from qiskit.quantum_info import Statevector, Operator
import qiskit

PAPER = 'Omanakuttan et al., arXiv:2504.01897v1 (2025)'

from circuit_logic import _positive_integer, _validate_angle, _normalize_clause, clause_compute, evaluate, phaser, mixer, zero_oracle, sat_oracle, qaoa, paper_iteration, qaoa_data_operator, resource_estimate, verify

def block(qc, n, label, name='block'):
    qc.append(Gate(name,n,[] ,label=label), range(n))

def draw_circuit(qc, ax, fontsize=12):
    """Correct Qiskit's user-Axes font scaling when equal aspect shrinks a tall plot."""
    width_before = ax.get_position().width
    qc.draw(output='mpl',ax=ax,fold=-1,
        style={'fontsize':fontsize,'subfontsize':fontsize-2},idle_wires=True)
    ax.figure.canvas.draw()
    factor = min(1.0, ax.get_position().width / width_before)
    if factor < .99:
        for item in ax.texts: item.set_fontsize(item.get_fontsize()*factor)
        for item in list(ax.lines)+list(ax.patches):
            item.set_linewidth(item.get_linewidth()*factor)

def atlas(out, data):
    plt.rcParams.update({'font.size':11,'svg.fonttype':'none','pdf.fonttype':42})
    circuits = []
    nshow = 4
    qc = QuantumCircuit(nshow,nshow)
    qc.h(range(nshow)); qc.barrier()
    block(qc,nshow,'U_QAOA\nT_U = p(T_ph + T_mix)','U')
    qc.barrier()
    block(qc,nshow,'O_C\nT_OC [Eq.10]','OC')
    block(qc,nshow,'U_QAOA_dg\nT_U','Udg')
    block(qc,nshow,'O_0\nT_O0 [Eq.11]','O0')
    block(qc,nshow,'U_QAOA\nT_U','U')
    qc.barrier(); qc.measure(range(nshow),range(nshow))
    circuits.append(('01_full_QAOA_AA',qc,'QAOA preparation + literal paper Eq.(6): time flows left to right',
        ['Four drawn data wires represent an arbitrary n-qubit register. Boxes are schematic, not executable.',
         'Initial H -> U_QAOA prepares |psi>. Repeat O_C -> U_dg -> O_0 -> U exactly R times.',
         'Each AA round: T_Q = 2p(T_phaser + T_mixer) + T_OC + T_O0. Eq.(7): T_q = R T_Q.',
         'Literal Eq.(6), no outer H; preparation convention differs from Eqs.(2)-(3). See reading audit.',
         'Initial preparation adds T_U (plus unspecified H/init costs). Final measurement/verification costs are unspecified.']))
    qc = QuantumCircuit(4)
    block(qc,4,'Phaser(gamma_l)\n(c+nP+12) T_LC\nEq.(9)','ph')
    qc.barrier(); qc.rx(Parameter('βl'),range(4))
    circuits.append(('02_QAOA_layer',qc,'One forward QAOA layer: phaser first, mixer second',
        ['Layer l: exp(-i beta_l H_M) exp(-i gamma_l H_C), Eqs.(3)-(5); repeat l=1,...,p.',
         'Parallel mixer: Rx(beta_l) on ALL n wires. T_mixer = nP T_LC [Eq.(8)], not n*nP*T_LC.',
         'Whole phaser: T_phaser = (c+nP+4 ceil(log2 k)) T_LC [Eq.(9)]. k=8 gives +12.',
         'One U_QAOA costs p(T_phaser+T_mixer). One U_dg costs the same in this resource model.']))
    qc = QuantumCircuit(4)
    qc.rx(-Parameter('βp'),range(4)); qc.barrier()
    block(qc,4,'Phaser(-gamma_p)\nT_phaser','phdg')
    qc.barrier(); qc.rx(-Parameter('β1'),range(4))
    block(qc,4,'Phaser(-gamma_1)\nT_phaser','phdg')
    circuits.append(('03_inverse_QAOA',qc,'Inverse QAOA: reverse layer order AND gate order',
        ['Shown: the last inverse layer p, then the first inverse layer 1; intermediate layers omitted.',
         'Forward layer: Phaser(gamma_l) -> Mixer(beta_l). Inverse: Mixer(-beta_l) -> Phaser(-gamma_l).',
         'Run layers p,p-1,...,1. Qiskit .inverse() performs both reversals and angle sign changes.',
         'The inverse contributes another p(T_phaser+T_mixer) in every AA round [Eq.(7)].']))
    n = 8
    c8 = [(i,i!=1) for i in range(n)]
    qc = phaser(n,[c8],Parameter('γ'))
    circuits.append(('04_8SAT_clause_phaser',qc,'Ideal 8-SAT phaser: positive phase follows Eqs.(3)-(4), unlike Eq.(20)',
        ['Clause: x0 OR NOT x1 OR x2 OR ... OR x7. Positive literals receive X around the MCX.',
         'P(+gamma) follows Eqs.(3)-(4); Eq.(20) prints the opposite sign. See the marked reading audit.',
         'This MCX drawing explains semantics. It is NOT the optimized lattice-surgery circuit used to obtain Eq.(9).',
         'Paper timing: one TACU phase gadget runs nP+4 ceil(log2 k) cycles; k=8 uses 7 CCZ states and 52 ancillas.',
         'All m clauses form c parallel batches; the FULL phaser time is (c+nP+12) T_LC, not m times this gadget.']))
    qc = QuantumCircuit(4)
    beta_l = Parameter('β')
    for i in range(4):
        qc.h(i); qc.p(-beta_l,i); qc.h(i)
    circuits.append(('05_mixer_phase_basis',qc,'Mixer as parallel phase gates in the X basis',
        ['Rx(beta)=exp(-i beta X/2) [paper Fig.1 caption; IBM RXGate definition].',
         'H P(-beta) H = exp(-i beta/2) Rx(beta); the difference is a global phase per wire.',
         'All n phase decompositions run in parallel with sufficient T-state factories.',
         'T_mixer = nP T_LC [Eq.(8)]; nP is decomposition logical-cycle cost, not QAOA depth p.']))
    clauses = [c8,[(i,i%2==0) for i in range(8)]]
    x = QuantumRegister(8,'x'); f = QuantumRegister(2,'f'); a = QuantumRegister(1,'all')
    qc = QuantumCircuit(x,f,a)
    for j,c in enumerate(clauses): qc.append(clause_compute(8,c).to_gate(label=f'C{j+1}'),list(x)+[f[j]])
    qc.ccx(f[0],f[1],a[0]); qc.z(a[0]); qc.ccx(f[0],f[1],a[0])
    for j in reversed(range(2)): qc.append(clause_compute(8,clauses[j]).inverse().to_gate(label=f'C{j+1} dg'),list(x)+[f[j]])
    circuits.append(('06_SAT_oracle',qc,'SAT oracle: compute clauses, AND, Z, uncompute',
        ['Executable illustration: n=8 variables, m=2 clauses, two clause flags and one all-clauses flag.',
         'O_C |x> = (-1)^(C1(x) AND ... AND Cm(x)) |x>. All ancillas return to |0>.',
         'Paper schedule: clause batches + binary AND trees + deliberate delays / ancilla recycling [Appendix C].',
         'FULL oracle time: T_OC = 4c log2(km/c) T_LC [Eq.(10)], including compute and uncompute.',
         'No separate paper formula allocates Eq.(10) exactly among these boxes; per-box timings are not invented.']))
    qc = zero_oracle(8)
    circuits.append(('07_zero_oracle',qc,'Zero-state oracle: X sandwich around an all-ones phase flip',
        ['O_0 = I - 2|0...0><0...0| = X^n [controlled phase pi] X^n.',
         'Only |0...0> receives a minus sign. H -> MCX -> H implements the all-ones controlled-Z phase.',
         'T_O0 = 4 log2(n) T_LC [Eq.(11)]; this is an approximate FULL oracle cost, not n separate costs.',
         'Paper implementation uses an n-qubit TACU gadget, n-1 CCZ states and logarithmic tree depth.',
         'O_0 is used directly in Eq.(6), with no surrounding full-register H layers.']))
    qc = QuantumCircuit(4)
    block(qc,4,'Startup\npart of task latency','startup')
    qc.barrier()
    block(qc,4,'Dispatch c batches\nc logical cycles','dispatch')
    qc.barrier()
    block(qc,4,'Finish\nremaining task work','finish')
    circuits.append(('08_phaser_timing_schedule',qc,'Phaser budget: dispatch plus startup and finish',
        ['Resource-budget schematic, not a serial gate schedule or the implemented MCX circuit.',
         'Dispatch c disjoint batches at one batch per logical cycle, with separate ancillas in flight.',
         'Startup before first dispatch plus finish after last dispatch fit within nP+4 ceil(log2 k).',
         'Single task: AND write 3L + phase nP + measurement clear L; L=ceil(log2 k).',
         'Source: p.11 Corollary IV.1 (upper bound), p.23 Appendix B; Eq.(9) uses c+nP+12 for k=8.']))
    entries=[]
    with PdfPages(out/'QAOA_AA_circuit_atlas.pdf') as pdf:
        for stem,qc,title,notes in circuits:
            fig = plt.figure(figsize=(18,11))
            ax = fig.add_axes([.045,.31,.91,.56])
            draw_circuit(qc, ax)
            fig.text(.045,.955,title,fontsize=19,weight='bold',va='top')
            fig.text(.045,.909,PAPER+' | logical-circuit view; time units: T_LC = d x 1 microsecond',fontsize=11,color='#475569')
            if stem == '01_full_QAOA_AA':
                fig.text(.105,.78,'INITIAL PREPARATION: ONCE',fontsize=12,weight='bold')
                fig.text(.47,.78,'ONE EQ.(6) ROUND: REPEAT R TIMES',fontsize=12,weight='bold')
            if stem == '06_SAT_oracle':
                fig.text(.33,.875,'FULL ORACLE: 4c log2(km/c) T_LC [Eq.(10)]',fontsize=12,weight='bold')
            if stem == '07_zero_oracle':
                fig.text(.33,.875,'FULL ORACLE: 4 log2(n) T_LC [Eq.(11)]',fontsize=12,weight='bold')
            for j,note in enumerate(notes): fig.text(.045,.255-.039*j,note,fontsize=11.4,va='top')
            fig.text(.045,.035,'Arrows/gates: left-to-right execution. Resource formulas belong to the paper compiler, not Qiskit circuit.depth().',fontsize=10,color='#475569')
            fig.savefig(out/(stem+'.png'),dpi=180,facecolor='white')
            fig.savefig(out/(stem+'.svg'),facecolor='white')
            pdf.savefig(fig); plt.close(fig)
            entries.append(dict(stem=stem,title=title,notes=notes))
        # Time budget: a Qiskit diagram with explicit numerical block costs.
        t=data['component_seconds']; p=data['p']; tu=data['T_U_seconds']
        qc=QuantumCircuit(4)
        for name,label in [('OC',f'O_C\n{t["OC"]:.4f} s'),('Udg',f'U_dg\n{tu:.4f} s'),('O0',f'O_0\n{t["O0"]*1e3:.4f} ms'),('U',f'U\n{tu:.4f} s')]: block(qc,4,label,name)
        fig=plt.figure(figsize=(18,11)); ax=fig.add_axes([.045,.48,.91,.37])
        draw_circuit(qc,ax,13)
        fig.text(.045,.955,'Numerical time example for ONE AA round (not a published crossover reproduction)',fontsize=18,weight='bold')
        fig.text(.045,.90,f'n={data["n"]}, m={data["m"]}, k=8, p={p}, c={data["c"]}, nP={data["nP"]}, d={data["d"]}; T_LC={data["d"]} microseconds',fontsize=12)
        lines=[f'T_mixer = {t["mixer"]*1e3:.3f} ms [Eq.8]; T_phaser = {t["phaser"]*1e3:.3f} ms [Eq.9].',
               f'One U: {tu:.6f} s. One AA round: {data["T_AA_round_seconds"]:.6f} s [bracket in Eq.7].',
               f'Modeled success probability = {data["success_model"]:.6g}; R = {data["R_eq7_continuous"]:.3f} (continuous asymptotic estimate).',
               f'Eq.(7) AA-only: {data["T_eq7_seconds"]/3600:.4f} h; plus one initial U: {data["T_with_initial_U_seconds"]/3600:.4f} h.',
               f'Main-text robust-AA overhead ~4x: {data["T_robust_main_text_approx_seconds"]/3600:.4f} h (protocol cost; Sec.II.B/IV.A).',
               'Paper budget only; not a success/runtime guarantee for the literal Eq.(6) simulator.',
               'c=2112 and nP=27 are selected illustrative inputs. Qiskit drawing qubits are NOT n=191 resource inputs.']
        for j,line in enumerate(lines): fig.text(.045,.415-.047*j,line,fontsize=12)
        fig.savefig(out/'09_numerical_timing.png',dpi=180,facecolor='white')
        fig.savefig(out/'09_numerical_timing.svg',facecolor='white'); pdf.savefig(fig);plt.close(fig)
        entries.append(dict(stem='09_numerical_timing',title='Numerical timing example',notes=lines))
    return entries

def reading_html(out, entries, data):
    descriptions = [
        '从全零态出发，先用 H 得到均匀叠加，再执行一次 QAOA。随后重复 AA：SAT oracle → 逆 QAOA → 全零态 oracle → 正向 QAOA，直接采用论文式 (6)。初态约定差异见下方原文对照。初始 QAOA 在重复框外，其成本需单独增加。',
        '每层先执行 phaser，再并行执行各比特的 Rx(β)。论文 H_M=(1/2)ΣX，所以角度是 β。一个层的时间是 T_phaser+T_mixer；p 层给出 T_U。',
        '逆电路同时反转层顺序和每层的门顺序，并把角度变号。最后一层先撤销 mixer，再撤销 phaser，直到第一层。每轮 AA 中正向与逆向各一次。',
        '真实 8-SAT 子句例子：计算 OR 到辅助位，施加 P(+γ)，反计算。H_C 的负号给出相位的正号。辅助位最后回到 |0>。MCX 表示功能；论文计时使用不同的 TACU 容错实现，不能从这张图的门深度直接得到。',
        '把 mixer 转到 X 基底：H P(-β) H 与 Rx(β) 只差整体相位。各根数据线并行，在足够资源态工厂的前提下，整段耗时是 nP 个逻辑周期，无须再乘 n。',
        '各子句 OR 先写入辅助位，再 AND 汇总，Z 标记整份 SAT 公式满足的赋值，最后全部反计算。公式 (10) 已包含正算与反算。m=2 的图用于解释；大 m 需要 AND 树和 Appendix C 的调度。',
        '全零态 oracle：X 全部数据位，给全 1 模式施加 π 相位，再 X 恢复。仅全零态被加负号。正文公式 (11) 是整段 oracle 的近似时间。',
        'c 批颜色相同的子句可以在批内并行；每周期派发一批，完整预算另含首次派发前准备与末次派发后收尾。由此得到 c+nP+12 周期，而不是把每个子句的完整延迟累加。此图是资源调度示意。',
        '数值例子采用 n=191、m=33616、p=253、d=29、c=2112、nP=27。c 与 nP 是明示的示例假设，未声称重现论文 64.57 小时的交叉点。所绘小电路与资源估算的大 n 参数分别使用。']
    formulas = [
        'T_Q = 2p(T_phaser + T_mixer) + T_OC + T_O0 ; T_q = R T_Q [Eq.(7)]',
        'T_U = p(T_phaser + T_mixer)',
        'T_U_dagger = T_U ; each AA round contains 2p phasers and 2p mixers',
        'T_phaser = (c + nP + 4 ceil(log2 k)) T_LC [Eq.(9)]',
        'T_mixer = nP T_LC [Eq.(8)]',
        'T_OC = 4c log2(km/c) T_LC [Eq.(10)]',
        'T_O0 = 4 log2(n) T_LC [Eq.(11)]',
        'dispatch: c T_LC ; startup + finish allowance: (nP + 12) T_LC for k=8',
        f'T_U = {data["T_U_seconds"]:.6f} s ; T_Q = {data["T_AA_round_seconds"]:.6f} s']
    titles=['整体 AA + QAOA','一层正向 QAOA','逆 QAOA','8-SAT 子句 Phaser','并行 Mixer','SAT Oracle','全零态 Oracle','Phaser 时间位置','数值计时例子']
    sections=[]
    for j,(e,desc,formula,title) in enumerate(zip(entries,descriptions,formulas,titles),1):
        img=base64.b64encode((out/(e['stem']+'.png')).read_bytes()).decode()
        sections.append(f'<section id="f{j}"><h2>{j}. {title}</h2><p>{desc}</p><div class="formula">{html.escape(formula)}</div><img src="data:image/png;base64,{img}" alt="{html.escape(e["title"])}"><p class="source">{PAPER}；具体原文页码与构造推导见完整中文说明。</p></section>')
    guide_path=Path(__file__).resolve().parent.parent/'notes'/'电路搭建与时间估算说明.md'
    guide=html.escape(guide_path.read_text(encoding='utf-8')) if guide_path.exists() else ''
    nav=' '.join(f'<a href="#f{j}">{j}. {title}</a>' for j,title in enumerate(titles,1))
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AA + QAOA 电路与计时</title><style>
    body{margin:0;background:#f4f5f7;color:#172033;font:16px/1.75 "Microsoft YaHei",system-ui,sans-serif}main{max-width:1260px;margin:auto;padding:40px 28px}h1{font-size:30px;margin-bottom:10px}h2{font-size:23px}p{max-width:1000px}nav{display:flex;flex-wrap:wrap;gap:10px 22px;margin:28px 0}a{color:#174b88}section{background:white;padding:24px;margin:24px 0;border:1px solid #d9dfe7}img{width:100%;height:auto}.formula{font-family:Consolas,monospace;background:#eef2f6;padding:15px;overflow:auto}.source{font-size:13px;color:#566477}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:15px/1.9 Consolas,"Microsoft YaHei",monospace}details{padding:20px;background:white}summary{cursor:pointer;font-weight:bold}</style><main>
    <h1>AA + QAOA：电路怎样搭，时间加在哪里</h1><p>电路使用 Qiskit 绘制，运行时间采用论文公式 (7)–(11) 的容错资源模型。T_LC=d×1 μs。门图解释逻辑功能，TACU 与工厂供应解释论文时间。</p>
    <p><a href="QAOA_AA_circuit_atlas.pdf">9 页电路图 PDF</a> · <a href="电路搭建与时间估算说明.md">完整中文推导与搭建说明</a> · <a href="build_circuits.py">Qiskit 源码</a> · <a href="time_estimates.json">数值参数与时间</a></p>
    <p>整体电路保留初始态制备，迭代中不添加 H 基底转换；原文没有单列的初始化、Clifford、测量与训练开销没有杜撰数字。稳健 AA 的约 4 倍开销属于重复尝试协议。</p>
    <nav>'''+nav+'</nav>'+''.join(sections)+'<details><summary>展开完整中文说明（Markdown 源文，含公式）</summary><pre>'+guide+'</pre></details></main></html>'
    page=page.replace('href="电路搭建与时间估算说明.md"', 'href="'+Path(os.path.relpath(guide_path,out)).as_posix()+'"')
    page=page.replace('href="build_circuits.py"', 'href="'+Path(os.path.relpath(Path(__file__).resolve(),out)).as_posix()+'"')
    (out/'阅读说明.html').write_text(page,encoding='utf-8')

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--output',type=Path,default=Path(__file__).resolve().parent.parent/'results'/'atlas')
    for name,default in [('n',191),('p',253),('d',29),('c',2112),('np',27)]:ap.add_argument('--'+name,type=int,default=default)
    ap.add_argument('--m',type=int,default=None)
    a=ap.parse_args();out=a.output;out.mkdir(parents=True,exist_ok=True)
    verification=verify();data=resource_estimate(a)
    (out/'verification.json').write_text(json.dumps(verification,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'time_estimates.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    with (out/'time_estimates.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.writer(f);writer.writerow(['component','equation','logical_cycles_per_call','seconds_per_call','calls_per_AA_round','seconds_per_AA_round'])
        for comp,eq,calls in [('mixer',8,2*a.p),('phaser',9,2*a.p),('OC',10,1),('O0',11,1)]:writer.writerow([comp,eq,data['component_logical_cycles'][comp],data['component_seconds'][comp],calls,calls*data['component_seconds'][comp]])
    n=8;clauses=[[(i,i!=1) for i in range(8)],[(i,i%2==0) for i in range(8)]]
    betas,gammas=[.41,.72],[.32,-.59]
    u=qaoa(n,clauses,betas,gammas);qc=QuantumCircuit(u.num_qubits,n)
    qc.h(range(n));qc.compose(u,inplace=True);qc.compose(paper_iteration(n,clauses,betas,gammas),inplace=True);qc.measure(range(n),range(n))
    qc.name='toy_8SAT_p2_R1'
    with (out/'executable_8SAT_example.qpy').open('wb') as f:qpy.dump(qc,f)
    (out/'executable_8SAT_example.txt').write_text(str(qc.draw('text',fold=160)),encoding='utf-8')
    entries=atlas(out,data)
    reading_html(out,entries,data)
    (out/'figure_index.json').write_text(json.dumps(entries,indent=2),encoding='utf-8')
    (out/'requirements.txt').write_text(f'qiskit=={qiskit.__version__}\nmatplotlib=={plt.matplotlib.__version__}\npylatexenc>=2.10\nnumpy>=2\n',encoding='utf-8')
    print(json.dumps({'verification':verification,'PDF':str(out/'QAOA_AA_circuit_atlas.pdf'),'figures':len(entries),'one_round_seconds':data['T_AA_round_seconds']},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
