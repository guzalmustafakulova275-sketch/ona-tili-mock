import os, sqlite3, secrets, csv, io, json, time
from datetime import datetime, timezone
from functools import wraps
from flask import Flask, request, jsonify, session, render_template, send_file, Response
from werkzeug.security import generate_password_hash, check_password_hash

BASE=os.path.dirname(os.path.abspath(__file__))
DB=os.path.join(BASE,'bilimtest.sqlite3')
app=Flask(__name__)
app.secret_key=os.environ.get('SECRET_KEY','change-this-secret-before-deploying')
ADMIN_PASSWORD=os.environ.get('ADMIN_PASSWORD','ahmadjon123')

def db():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

def init_db():
    c=db(); c.executescript('''
    CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS exams (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, code TEXT NOT NULL, duration INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'waiting', start_at REAL, end_at REAL, published INTEGER NOT NULL DEFAULT 0, created_at REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS participants (id INTEGER PRIMARY KEY AUTOINCREMENT, exam_id INTEGER NOT NULL, name TEXT NOT NULL, token TEXT NOT NULL UNIQUE, status TEXT NOT NULL DEFAULT 'waiting', joined_at REAL NOT NULL, submitted_at REAL, FOREIGN KEY(exam_id) REFERENCES exams(id));
    CREATE TABLE IF NOT EXISTS answers (id INTEGER PRIMARY KEY AUTOINCREMENT, participant_id INTEGER NOT NULL, question_no INTEGER NOT NULL, answer TEXT NOT NULL DEFAULT '', updated_at REAL NOT NULL, UNIQUE(participant_id,question_no), FOREIGN KEY(participant_id) REFERENCES participants(id));
    CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY AUTOINCREMENT, exam_title TEXT NOT NULL, code TEXT NOT NULL, started_at REAL, ended_at REAL, participants INTEGER NOT NULL, created_at REAL NOT NULL, summary TEXT NOT NULL DEFAULT '');
    CREATE TABLE IF NOT EXISTS questions (exam_id INTEGER NOT NULL, question_no INTEGER NOT NULL, data TEXT NOT NULL, PRIMARY KEY(exam_id,question_no));
    ''')
    defaults={'duration':'180','code':'T151','title':'Ona tili va adabiyot — T-151'}
    for k,v in defaults.items(): c.execute('INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)',(k,v))
    if not c.execute('SELECT id FROM exams WHERE status IN (\'waiting\',\'running\') ORDER BY id DESC LIMIT 1').fetchone():
        c.execute('INSERT INTO exams(title,code,duration,status,created_at) VALUES(?,?,?,?,?)',(defaults['title'],defaults['code'],180,'waiting',time.time()))
    c.commit(); c.close()

def setting(k):
    c=db(); r=c.execute('SELECT value FROM settings WHERE key=?',(k,)).fetchone(); c.close(); return r['value'] if r else ''
def current_exam(c=None):
    own=c is None; c=c or db(); r=c.execute("SELECT * FROM exams WHERE status IN ('waiting','running') ORDER BY id DESC LIMIT 1").fetchone()
    if own:c.close()
    return r

def admin_required(fn):
    @wraps(fn)
    def w(*a,**kw):
        if not session.get('admin'): return jsonify(error='Admin ruxsati kerak'),401
        return fn(*a,**kw)
    return w

def student_from_request(c):
    token=request.headers.get('X-Student-Token') or request.args.get('token')
    return c.execute('SELECT * FROM participants WHERE token=?',(token,)).fetchone() if token else None

def load_questions(c, exam_id):
    rows=c.execute('SELECT question_no,data FROM questions WHERE exam_id=? ORDER BY question_no',(exam_id,)).fetchall()
    d={r['question_no']:json.loads(r['data']) for r in rows}
    return [d.get(i, {'number':i,'type':'open' if i>=36 else 'choice','text':f'{i}-savol','options':[],'placeholder': 'Savol matni tayyor test faylidan yuklanadi.'}) for i in range(1,45)]

@app.route('/')
def home(): return render_template('index.html')
@app.get('/api/status')
def status():
    c=db(); e=c.execute('SELECT * FROM exams ORDER BY id DESC LIMIT 1').fetchone()
    if not e: c.close(); return jsonify(exam=None)
    q=c.execute('SELECT COUNT(*) n FROM participants WHERE exam_id=?',(e['id'],)).fetchone()['n']
    c.close(); return jsonify(exam=dict(e),participants=q,server_time=time.time())
@app.post('/api/admin/login')
def admin_login():
    data=request.get_json() or {}
    if secrets.compare_digest(str(data.get('password','')),ADMIN_PASSWORD): session['admin']=True; return jsonify(ok=True)
    return jsonify(error='Parol noto‘g‘ri'),401
@app.post('/api/admin/logout')
def admin_logout(): session.clear(); return jsonify(ok=True)
@app.get('/api/admin/overview')
@admin_required
def overview():
    c=db(); e=c.execute('SELECT * FROM exams ORDER BY id DESC LIMIT 1').fetchone()
    if not e: c.close(); return jsonify(exam=None,participants=[],history=[])
    ps=c.execute('''SELECT p.*, (SELECT COUNT(*) FROM answers a WHERE a.participant_id=p.id AND a.answer!='') answered FROM participants p WHERE exam_id=? ORDER BY joined_at''',(e['id'],)).fetchall()
    hist=c.execute('SELECT * FROM history ORDER BY id DESC LIMIT 30').fetchall()
    c.close(); return jsonify(exam=dict(e),participants=[dict(x) for x in ps],history=[dict(x) for x in hist],questions=load_questions(db(),e['id']))
@app.post('/api/student/join')
def student_join():
    d=request.get_json() or {}; name=str(d.get('name','')).strip(); code=str(d.get('code','')).strip().upper(); c=db(); e=current_exam(c)
    if not name: c.close(); return jsonify(error='Ism-familiyani kiriting'),400
    if not e or code != e['code'].upper(): c.close(); return jsonify(error='Imtihon kodi noto‘g‘ri yoki imtihon mavjud emas'),400
    if e['status']!='waiting': c.close(); return jsonify(error='Imtihon boshlangan. Yangi ishtirokchi qabul qilinmaydi.'),409
    token=secrets.token_urlsafe(32); cur=c.execute('INSERT INTO participants(exam_id,name,token,status,joined_at) VALUES(?,?,?,?,?)',(e['id'],name,token,'waiting',time.time())); c.commit(); pid=cur.lastrowid; c.close()
    return jsonify(token=token,participant_id=pid,name=name)
@app.get('/api/student/state')
def student_state():
    c=db(); p=student_from_request(c)
    if not p: c.close(); return jsonify(error='O‘quvchi sessiyasi topilmadi'),401
    e=c.execute('SELECT * FROM exams WHERE id=?',(p['exam_id'],)).fetchone(); ans=c.execute('SELECT question_no,answer FROM answers WHERE participant_id=?',(p['id'],)).fetchall(); questions=load_questions(c,e['id']); c.close()
    return jsonify(participant=dict(p),exam=dict(e),answers={str(x['question_no']):x['answer'] for x in ans},questions=questions,server_time=time.time())
@app.post('/api/student/answer')
def student_answer():
    d=request.get_json() or {}; c=db(); p=student_from_request(c)
    if not p: c.close(); return jsonify(error='Sessiya topilmadi'),401
    e=c.execute('SELECT * FROM exams WHERE id=?',(p['exam_id'],)).fetchone()
    if e['status']!='running' or p['status']=='submitted' or time.time()>=e['start_at']+e['duration']*60: c.close(); return jsonify(error='Javob qabul qilish vaqti tugagan'),409
    try: n=int(d.get('number')); val=str(d.get('answer',''))
    except: c.close(); return jsonify(error='Javob formati xato'),400
    if n<1 or n>44: c.close(); return jsonify(error='Savol raqami xato'),400
    c.execute('INSERT INTO answers(participant_id,question_no,answer,updated_at) VALUES(?,?,?,?) ON CONFLICT(participant_id,question_no) DO UPDATE SET answer=excluded.answer,updated_at=excluded.updated_at',(p['id'],n,val,time.time())); c.commit(); c.close(); return jsonify(ok=True)
@app.post('/api/student/submit')
def student_submit():
    c=db(); p=student_from_request(c)
    if not p: c.close(); return jsonify(error='Sessiya topilmadi'),401
    c.execute("UPDATE participants SET status='submitted',submitted_at=? WHERE id=?",(time.time(),p['id'])); c.commit(); c.close(); return jsonify(ok=True)
@app.post('/api/admin/exam/start')
@admin_required
def start_exam():
    c=db(); e=current_exam(c)
    if not e: c.close(); return jsonify(error='Faol imtihon yo‘q'),400
    if e['status']=='running': c.close(); return jsonify(ok=True)
    now=time.time(); c.execute("UPDATE exams SET status='running',start_at=?,end_at=NULL,published=0 WHERE id=?",(now,e['id'])); c.execute("UPDATE participants SET status='running' WHERE exam_id=? AND status='waiting'",(e['id'],)); c.commit(); c.close(); return jsonify(ok=True,start_at=now)
@app.post('/api/admin/exam/end')
@admin_required
def end_exam():
    c=db(); e=current_exam(c)
    if not e: c.close(); return jsonify(error='Faol imtihon yo‘q'),400
    now=time.time(); c.execute("UPDATE exams SET status='ended',end_at=? WHERE id=?",(now,e['id'])); c.execute("UPDATE participants SET status='submitted',submitted_at=COALESCE(submitted_at,?) WHERE exam_id=? AND status!='submitted'",(now,e['id'])); c.commit(); c.close(); return jsonify(ok=True)
@app.post('/api/admin/exam/reset')
@admin_required
def reset_exam():
    d=request.get_json() or {}; c=db(); e=current_exam(c)
    if e and e['status']=='running': c.close(); return jsonify(error='Avval joriy imtihonni yakunlang'),409
    title=str(d.get('title') or setting('title')); code=str(d.get('code') or setting('code')).upper(); duration=max(5,min(600,int(d.get('duration') or setting('duration'))))
    c.execute('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',('title',title)); c.execute('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',('code',code)); c.execute('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',('duration',str(duration)))
    cur=c.execute('INSERT INTO exams(title,code,duration,status,created_at) VALUES(?,?,?,?,?)',(title,code,duration,'waiting',time.time())); c.commit(); c.close(); return jsonify(ok=True,exam_id=cur.lastrowid)
@app.post('/api/admin/publish')
@admin_required
def publish():
    c=db(); e=c.execute("SELECT * FROM exams WHERE status='ended' ORDER BY id DESC LIMIT 1").fetchone()
    if not e: c.close(); return jsonify(error='Yakunlangan imtihon topilmadi'),400
    c.execute('UPDATE exams SET published=1 WHERE id=?',(e['id'],)); n=c.execute('SELECT COUNT(*) n FROM participants WHERE exam_id=?',(e['id'],)).fetchone()['n']
    c.execute('INSERT INTO history(exam_title,code,started_at,ended_at,participants,created_at,summary) VALUES(?,?,?,?,?,?,?)',(e['title'],e['code'],e['start_at'],e['end_at'],n,time.time(),'Natijalar admin tomonidan e’lon qilindi'))
    c.commit(); c.close(); return jsonify(ok=True)
@app.post('/api/admin/settings')
@admin_required
def save_settings():
    d=request.get_json() or {}; c=db()
    for k in ('title','code','duration'):
        if k in d: c.execute('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(k,str(d[k])))
    c.commit(); c.close(); return jsonify(ok=True)
@app.post('/api/admin/questions/import')
@admin_required
def import_questions():
    d=request.get_json() or {}; qs=d.get('questions')
    if not isinstance(qs,list) or len(qs)!=44: return jsonify(error='JSON ichida aynan 44 ta savol bo‘lishi kerak'),400
    c=db(); e=current_exam(c)
    if not e or e['status']!='waiting': c.close(); return jsonify(error='Savollar faqat imtihon boshlanmasidan oldin yuklanadi'),409
    for i,q in enumerate(qs,1):
        if not isinstance(q,dict) or not str(q.get('text','')).strip(): c.close(); return jsonify(error=f'{i}-savol matni yo‘q'),400
        c.execute('INSERT OR REPLACE INTO questions(exam_id,question_no,data) VALUES(?,?,?)',(e['id'],i,json.dumps(q,ensure_ascii=False)))
    c.commit(); c.close(); return jsonify(ok=True)
@app.get('/api/admin/export.csv')
@admin_required
def export_csv():
    c=db(); e=c.execute('SELECT * FROM exams ORDER BY id DESC LIMIT 1').fetchone(); out=io.StringIO(); w=csv.writer(out); w.writerow(['O‘quvchi','Holat']+[f'{i}-savol' for i in range(1,45)])
    if e:
        for p in c.execute('SELECT * FROM participants WHERE exam_id=?',(e['id'],)).fetchall():
            a={x['question_no']:x['answer'] for x in c.execute('SELECT question_no,answer FROM answers WHERE participant_id=?',(p['id'],)).fetchall()}; w.writerow([p['name'],p['status']]+[a.get(i,'') for i in range(1,45)])
    c.close(); return Response('\ufeff'+out.getvalue(),mimetype='text/csv',headers={'Content-Disposition':'attachment; filename=bilimtest_natijalar.csv'})
@app.get('/api/student/result')
def student_result():
    c=db(); p=student_from_request(c)
    if not p: c.close(); return jsonify(error='Sessiya topilmadi'),401
    e=c.execute('SELECT * FROM exams WHERE id=?',(p['exam_id'],)).fetchone()
    if not e['published']: c.close(); return jsonify(published=False)
    a=c.execute('SELECT COUNT(*) n FROM answers WHERE participant_id=? AND answer!=""',(p['id'],)).fetchone()['n']; c.close(); return jsonify(published=True,answered=a,total=44,message='Rasmiy Rasch balli kalibrlash parametrlari va baholash kalitisiz hisoblanmaydi.')

if __name__=='__main__':
    init_db(); app.run(host='0.0.0.0',port=int(os.environ.get('PORT',5000)),debug=False)
else: init_db()
