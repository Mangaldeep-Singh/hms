import os, time
from datetime import datetime
from werkzeug.utils import secure_filename
from passlib.hash import sha256_crypt
from flask import Flask, request, render_template, flash, redirect, url_for, session, logging, jsonify
from forms import LoginForm, CreateCustomer,CreateDiagnostic,SearchCustomer, CreateMedicine, UpdateCustomer, DepositAmount, CashTransfer, CreateAccount, UpdateAccount, WithdrawAmount, CreateExecutive, CustomerAccount
from flask_mysqldb import MySQL
app = Flask(__name__)

app.secret_key = 'retailBanking'

app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_DB'] = 'hms1'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login',methods=["GET","POST"])
def login():
    if session.get('logged_in'):
        return(redirect(url_for('dashboard')))
    form = LoginForm(request.form)
    if request.method == 'POST':
        username = request.form['username']
        user_pass = request.form['password']
        cur = mysql.connection.cursor()
        result = cur.execute("SELECT * FROM userstore WHERE username = %s AND isActive = 'active' ",[username])
        if result > 0:
            data = cur.fetchone()
            password = data['password']
            userlevel = data['userlevel']
            if userlevel == 0:
                permission = 'Admin'
            elif userlevel == 1:
                permission = 'Excecutive'
            elif userlevel == 2:
                permission = 'Diagnostic'
            elif userlevel == 3:
                permission = 'Pharmacist'

            if sha256_crypt.verify(user_pass, password):
                session['logged_in']    = True
                session['userlevel']    = userlevel
                session['username']     = username
                session['permission']   = permission
                flash('Logged In Successfully!!!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid Login', 'danger')
                return redirect(url_for('login'))
        else:
            flash('User Not Found', 'danger')
            return redirect(url_for('login'))
            
    return render_template('login.html',form=form)

@app.route("/bill",methods=["GET","POST"])
def bill():
    
    if session.get('logged_in'):
        if  (session.get('userlevel') == 0 or session.get('userlevel') == 1):
            detail=None
            id=None            
            title = ['Patient Bill','Generate Patient bill Here','']
            cur = mysql.connection.cursor()
            form =SearchCustomer()
            if request.method == 'POST' and form.validate():
                id = request.form['search']
                cur.execute("select * from bill where billstatus = 'pending' AND patientID = %s",[id])
                bill = cur.fetchall()
                
            extra = []
            date = datetime.today().strftime('%Y-%m-%d')
            cur.execute("select *, DATEDIFF (%s, doa) as totaldate  from patients where isDel = '0' AND patientID = %s AND isActive='active'",[date,id])
            patient = cur.fetchone()
            cur.execute("select * from bill where billstatus = 'pending' AND patientID = %s",[id])
            bill = cur.fetchall()
            if(patient):
                if(patient['totaldate'] <= 0):
                    patient['totaldate'] = 1
                if(patient['btype'] == 'semi'):
                    extra.append('Semi sharing')
                    extra.append(4000.0)
                elif(patient['btype'] == 'general'):
                    extra.append('General ward')
                    extra.append(2000.0)
                elif(patient['btype'] == 'single'):
                    extra.append('Single Room')
                    extra.append(8000.0)
                extra.append(date)
                total = 0
                for i in bill:
                    total += (int(i['quantity'])*float(i['rate']))
                atot = total+ (float(extra[1])*float(patient['totaldate']))
                extra.append(atot)
            return render_template('bill_gen.html',form=form,title=title,patient=patient,bill=bill,extra=extra)
        
        else:
            flash('Session Timeout', 'danger')
            return redirect(url_for('login'))
    else:
        flash('Access Denied', 'danger')
        return redirect(url_for('logout'))

@app.route("/createmedicine",methods=["GET","POST"])
def createmedicine():
    if session.get('logged_in'):
        if (session.get('userlevel') == 0 or session.get('userlevel') == 1):
            title = ['Pharmacy', 'Add Medicine to Stock', '']  
            form = CreateMedicine()
            cur = mysql.connection.cursor()
            if request.method == 'POST' and form.validate():
                medicinename = request.form['name']
                quantity = request.form['quantity']
                generateid = str(int(time.time()))
                id = int(generateid[0:2]+generateid[3:])
                rate = request.form['rate']
                cur.execute("SELECT * FROM `medmaster` WHERE `name` = %s ",[medicinename])
                checkpatient = cur.fetchone()
                if checkpatient :
                    if(cur.execute('''Insert into medmaster (medID, name, quantity, price) VALUES (%s,%s, %s, %s)''', (id, medicinename, quantity, rate ))):
                        mysql.connection.commit()
                        cur.close()
                        flash('Created Successfully!!', 'success')
                        return redirect(url_for('createmedicine'))
                    else:
                        flash('Something went wrong', 'danger')
                        return redirect(url_for('createmedicine'))
                else:
                    flash('Medicine already exist', 'danger')
                    return redirect(url_for('createmedicine'))
            return render_template('create_medicine.html',title=title,form=form)
        else:
            flash('Session Timeout', 'danger')
            return redirect(url_for('login'))
    else:
        flash('Access Denied', 'danger')
        return redirect(url_for('logout'))

@app.route("/removemed",methods=["GET","POST"])
def removemed():
    if session.get('logged_in'):
        if  (session.get('userlevel') == 0 or session.get('userlevel') == 1):
            data=""
            title = ['Delete Medicine','Remove Medicine from Inventory','']
            cur = mysql.connection.cursor()
            form =SearchCustomer()
            
            if request.method == 'POST' and form.validate():
                id = request.form['searchname']
                print(id)
                check = cur.execute("UPDATE medmaster SET remove = %s where name = %s", ( '1', id))
                if(check):
                    mysql.connection.commit()
                    cur.close()
                    flash('Deleted Successfully!!', 'success')
                    return redirect(url_for('deletepatient'))
                else:
                    flash('Something went wrong', 'danger')
                    return redirect(url_for('deletepatient'))

            return render_template('remove_medicine.html',title=title,form=form)
        else:
            flash('Session Timeout', 'danger')
            return redirect(url_for('login'))
    else:
        flash('Access Denied', 'danger')
        return redirect(url_for('logout'))

@app.route('/getpatientdetail',methods=["GET"])
def getpatientdetail():
    if session.get('logged_in'):
        if(session.get('userlevel') == 0 or session.get('userlevel') == 1):
            cur = mysql.connection.cursor()
            cur.execute("SELECT * from medmaster where name = %s AND remove = '0' ", [ request.args.get('pid') ])
            detail = cur.fetchone()
            return jsonify(detail)
        else:
            return jsonify(None)
    else:
        return jsonify(None)

@app.route("/viewmed")
def viewmed():
    if session.get('logged_in'):
        if (session.get('userlevel') == 0 or session.get('userlevel') == 1):    
            title = ['Manage medicines','List of all Medicines','']
            cur = mysql.connection.cursor()
            cur.execute("SELECT * from medmaster where remove = 0")
            detail = cur.fetchall()
            return render_template('manage_medicine.html',title=title, detail=detail)
        else:
            flash('Session Timeout', 'danger')
            return redirect(url_for('login'))
    else:
        flash('Access Denied', 'danger')
        return redirect(url_for('logout'))
@app.route("/updatemed")
def updatemed():
    pass
@app.route("/creatediag",methods=["GET","POST"])
def creatediag():
    if session.get('logged_in'):
        if (session.get('userlevel') == 0 or session.get('userlevel') == 1):
            title = ['Diagnostics', 'Add Diagnostic Tets', '']  
            form = CreateDiagnostic()
            cur = mysql.connection.cursor()
            if request.method == 'POST' and form.validate():
                medicinename = request.form['name']
                generateid = str(int(time.time()))
                id = int(generateid[0:2]+generateid[3:])
                rate = request.form['rate']
                cur.execute("select name from diagnosticmaster where name = %s ",[medicinename])
                checkpatient = cur.fetchone()
                if checkpatient  == False:
                    if(cur.execute('''Insert into diagnosticmaster (testID, name, price) VALUES (%s,%s,  %s)''', (id, medicinename,  rate ))):
                        mysql.connection.commit()
                        cur.close()
                        flash('Created Successfully!!', 'success')
                        return redirect(url_for('createmedicine'))
                    else:
                        flash('Something went wrong', 'danger')
                        return redirect(url_for('createmedicine'))
                else:
                    flash('Medicine already exist', 'danger')
                    return redirect(url_for('createmedicine'))
            return render_template('create_diagnostic.html',title=title,form=form)
        else:
            flash('Session Timeout', 'danger')
            return redirect(url_for('login'))
    else:
        flash('Access Denied', 'danger')
        return redirect(url_for('logout'))

@app.route("/removediag")
def removediag():
    pass
@app.route("/viewdiag")
def viewdiag():
    pass
@app.route("/updatediag")
def updatediag():
    pass
@app.route("/issuemed",methods=["GET","POST"])
def issuemed():
    if session.get('logged_in'):
        if  (session.get('userlevel') == 0 or session.get('userlevel') == 1 or session.get('userlevel') == 2 or session.get('userlevel') == 3):
            detail=""
            pharmacy=""
            med = ""
            title = ['Patient History','Patient Diagnostic Test History','']
            subtitle = ['Medicine','Diagnostics Conducted','']
            cur = mysql.connection.cursor()
            form =SearchCustomer()
            if request.method == 'POST' and form.validate():
                id = request.form['search']
                
                cur.execute("SELECT * from patients where patientID = %s", [ id ])
                detail = cur.fetchone()
                cur.execute("SELECT * from medmaster")
                med = cur.fetchall()
                
                if med == None:
                    flash('Invalid patient Id, patient not found', 'danger')
                    return redirect(url_for('issuemed'))
                if detail == None:
                    flash('Invalid patient Id, patient not found', 'danger')
                    return redirect(url_for('issuemed'))
                cur.execute("SELECT * FROM `trackpatmed` WHERE `patientID` = %s", [ id ])
                pharmacy=cur.fetchall()
                if pharmacy == None:
                    flash('No Medicine Issued', 'danger')
                    return redirect(url_for('issuemed'))
                    
            return render_template('perform_task.html',form=form,title=title,subtitle=subtitle,detail=detail,pharmacy=pharmacy,med=med)
        
        else:
            flash('Session Timeout', 'danger')
            return redirect(url_for('login'))
    else:
        flash('Access Denied', 'danger')
        return redirect(url_for('logout'))
@app.route("/diagtest")
def diagtest():
    if session.get('logged_in'):
        if  (session.get('userlevel') == 0 or session.get('userlevel') == 1 or session.get('userlevel') == 2 or session.get('userlevel') == 3):
            detail=""
            pharmacy=""
            title = ['Patient History','Patient Diagnostic Test History','']
            subtitle = ['Diagnostic','Diagnostics Conducted','']
            cur = mysql.connection.cursor()
            form =SearchCustomer()
            if request.method == 'POST' and form.validate():
                id = request.form['search']
                cur.execute("SELECT * from patients where patientID = %s", [ id ])
                detail = cur.fetchone()
                if detail == None:
                    flash('Invalid patient Id, patient not found', 'danger')
                    return redirect(url_for('patientmeddetail'))
                cur.execute("SELECT * FROM `trackpatmed` WHERE `patientID` = %s", [ id ])
                pharmacy=cur.fetchall()
                if pharmacy == None:
                    flash('No Medicine Issued', 'danger')
                    return redirect(url_for('patientmeddetail'))
                    
            return render_template('perform_task.html',form=form,title=title,subtitle=subtitle,detail=detail,pharmacy=pharmacy)
        
        else:
            flash('Session Timeout', 'danger')
            return redirect(url_for('login'))
    else:
        flash('Access Denied', 'danger')
        return redirect(url_for('logout'))
@app.route('/logout')
def logout():
    session.pop('logged_in',False)
    session.pop('permission',False)
    session.pop('username',False)
    session.pop('userlevel',False)
    return redirect(url_for('login'))

@app.route('/patientmeddetail',methods=["GET","POST"])
def patientmeddetail():
    if session.get('logged_in'):
        if  (session.get('userlevel') == 0 or session.get('userlevel') == 1 or session.get('userlevel') == 2 or session.get('userlevel') == 3):
            detail=""
            pharmacy=""
            title = ['Patient History','Patient Pharmacy History','']
            subtitle = ['Pharmacy','Medicine Issued','']
            cur = mysql.connection.cursor()
            form =SearchCustomer()
            if request.method == 'POST' and form.validate():
                id = request.form['search']
                cur.execute("SELECT * from patients where patientID = %s", [ id ])
                detail = cur.fetchone()
                if detail == None:
                    flash('Invalid patient Id, patient not found', 'danger')
                    return redirect(url_for('patientmeddetail'))
                cur.execute("SELECT * FROM `trackpatmed` WHERE `patientID` = %s", [ id ])
                pharmacy=cur.fetchall()
                if pharmacy == None:
                    flash('No Medicine Issued', 'danger')
                    return redirect(url_for('patientmeddetail'))
                    
            return render_template('user_detail.html',form=form,title=title,subtitle=subtitle,detail=detail,pharmacy=pharmacy)
        
        else:
            flash('Session Timeout', 'danger')
            return redirect(url_for('login'))
    else:
        flash('Access Denied', 'danger')
        return redirect(url_for('logout'))

@app.route('/patientdiagdetail',methods=["GET","POST"])
def patientdiagdetail():
    if session.get('logged_in'):
        if  (session.get('userlevel') == 0 or session.get('userlevel') == 1 or session.get('userlevel') == 2 or session.get('userlevel') == 3):
            detail=""
            pharmacy=""
            title = ['Patient History','Patient Diagnostic Test History','']
            subtitle = ['Diagnostic','Diagnostics Conducted','']
            cur = mysql.connection.cursor()
            form =SearchCustomer()
            if request.method == 'POST' and form.validate():
                id = request.form['search']
                cur.execute("SELECT * from patients where patientID = %s", [ id ])
                detail = cur.fetchone()
                if detail == None:
                    flash('Invalid patient Id, patient not found', 'danger')
                    return redirect(url_for('patientmeddetail'))
                cur.execute("SELECT * FROM `trackpatmed` WHERE `patientID` = %s", [ id ])
                pharmacy=cur.fetchall()
                if pharmacy == None:
                    flash('No Medicine Issued', 'danger')
                    return redirect(url_for('patientmeddetail'))
                    
            return render_template('user_detail.html',form=form,title=title,subtitle=subtitle,detail=detail,pharmacy=pharmacy)
        
        else:
            flash('Session Timeout', 'danger')
            return redirect(url_for('login'))
    else:
        flash('Access Denied', 'danger')
        return redirect(url_for('logout'))



#dashboard
@app.route('/dashboard')
def dashboard():
    if session.get('logged_in') and (session.get('userlevel') == 0 or session.get('userlevel') == 1 or session.get('userlevel') == 2):
        title = ['Dashboard','All Details Available','']
        cur = mysql.connection.cursor()
        cur.execute("SELECT count(*)  from patients where  isDel = 0 AND isActive = 'active'")
        a = cur.fetchone()
        cur.execute("SELECT count(*)  from patients where  isDel <> 0 or isActive ='discharged'")
        b = cur.fetchone()
        l = [a,b]
        return render_template('dashboard.html',title=title, detail=l)
    else:
        flash('Access Denied', 'danger')
        return redirect(url_for('logout'))


#Customer section
@app.route('/createCustomer',methods=["GET","POST"])
def createcustomer():
    if session.get('logged_in'):
        if  (session.get('userlevel') == 0 or session.get('userlevel') == 1):    
            form = CreateCustomer()
            title = ['Create Customer','Fill all the fields to create customer','']
            if request.method == 'POST' and form.validate():
                ssnid = form.ssnid.data
                name = form.name.data
                age = form.age.data
                doa = datetime.today().strftime('%Y-%m-%d')
                bt = form.bed.data
                address = form.address.data
                state = form.state.data
                city = form.city.data
                generate = str(int(time.time()))
                id = int(generate[0:1]+generate[2:])
                state = form.state.data
                city = form.city.data
                cur = mysql.connection.cursor()
                checkcustomer= cur.execute("select SSNID from patients where SSNID = %s ",[ssnid])
                if checkcustomer == False:
                    if(cur.execute('''INSERT INTO `patients`( `SSNID`, `patientID`, `name`, `age`, `doa`, `btype`, `address`, `city`, `state`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)''', ( ssnid, id, name, age,doa,bt, address, city,state))):
                        mysql.connection.commit()
                        cur.close()
                        flash('Created Successfully!!', 'success')
                        return redirect('createCustomer')
                    else:
                        flash('Something went wrong', 'danger')
                        return redirect('createCustomer')
                else:
                    flash(f"Customer account with SSN ID - {ssnid} already exists !", "danger")
                    return redirect(url_for('createcustomer'))

            return render_template('create_customer.html',title=title,form=form)
        else:
            flash('Session Timeout', 'danger')
            return redirect(url_for('login'))
    else:
        flash('Access Denied', 'danger')
        return redirect(url_for('logout'))

@app.route('/updatecustomerdetails')
def updatecustomerdetails():
    if session.get('logged_in'):
        if (session.get('userlevel') == 0 or session.get('userlevel') == 1):    
            title = ['Manage Customer','List of all Customer','']
            cur = mysql.connection.cursor()
            cur.execute("SELECT * from patients where isDel = 0 and isActive = 'active'")
            detail = cur.fetchall()
            return render_template('manage_customer.html',title=title, detail=detail)
        else:
            flash('Session Timeout', 'danger')
            return redirect(url_for('login'))
    else:
        flash('Access Denied', 'danger')
        return redirect(url_for('logout'))

@app.route('/getcustomerdetail',methods=["GET"])
def getcustomerdetail():
    if session.get('logged_in'):
        if  (session.get('userlevel') == 0 or session.get('userlevel') == 1):
            cur = mysql.connection.cursor()
            print(request.args.get('cid'))
            cur.execute("SELECT * from patients where patientID = %s", [ request.args.get('cid') ])
            detail = cur.fetchone()
            return jsonify(detail)
        else:
            flash('Session Timeout', 'danger')
            return redirect(url_for('login'))
    else:
        flash('Access Denied', 'danger')
        return redirect(url_for('logout'))

@app.route('/editcustomerdetail/<id>',methods=["GET","POST"])
def editcustomerdetail(id):
    if session.get('logged_in'):
        if  (session.get('userlevel') == 0 or session.get('userlevel') == 1):
            detail = None
            title = ['Update Customer','Edit Customer Details','']
            cur = mysql.connection.cursor()
            form = UpdateCustomer()
            if(request.method == "GET"):
                cur.execute("SELECT * from patients where patientID = %s", [ id ])
                detail = cur.fetchone()
            if(request.method == 'POST') and form.validate():
                id = request.form['id']
                name = form.name.data
                age = form.age.data
                doa = form.doa.data
                bt = form.bed.data
                address = form.address.data
                state = form.state.data
                city = form.city.data
                check = cur.execute("UPDATE patients SET name = %s, age = %s, doa = %s, btype = %s, address = %s, city = %s, state= %s where patientID = %s", ( name,age,doa,bt,address, city, state, id ))
                if(check):
                    mysql.connection.commit()
                    flash('Updated Successfully!!', 'success')
                    return redirect(url_for("updatecustomerdetails"))
                else:
                    flash('No row Affected or Something Went Wrong', 'danger')
                    return redirect(url_for("updatecustomerdetails"))
                    
            return render_template('edit_customer.html',form=form,title=title,detail=detail)
        else:
            flash('Session Timeout', 'danger')
            return redirect(url_for('login'))
    else:
        flash('Access Denied', 'danger')
        return redirect(url_for('logout'))

@app.route('/deletecustomerdetail/<id>',methods=["PUT"])
def deletecustomerdetail(id):
    if session.get('logged_in'):
        if  (session.get('userlevel') == 0 or session.get('userlevel') == 1):
            cur = mysql.connection.cursor()
            check = cur.execute("UPDATE patients SET isDel = %s where patientID = %s",( 1, id ))
            mysql.connection.commit()
            if(check):
                return jsonify('true')
            else:
                return False
        else:
            flash('Session Timeout', 'danger')
            return redirect(url_for('login'))
    else:
        flash('Access Denied', 'danger')
        return redirect(url_for('logout'))

@app.route('/customerstatus/',methods=["GET","POST"])
def customerstatus():
    if session.get('logged_in'):
        if  (session.get('userlevel') == 0 or session.get('userlevel') == 1):
            detail=""
            title = ['Customer Status','Status of all Customer Here','']
            cur = mysql.connection.cursor()
            form =SearchCustomer()
            
            if request.method == 'POST' and form.validate():
                id = request.form['search']
                print(id)
                cur.execute("SELECT * from patients where patientID = %s", [ id ])
                detail = cur.fetchone()
                if detail == None:
                    flash('Invalid patient Id, patient not found', 'danger')
                    return redirect(url_for('customerstatus'))
            return render_template('status_customer.html',form=form,title=title,detail=detail)
        
        else:
            flash('Session Timeout', 'danger')
            return redirect(url_for('login'))
    else:
        flash('Access Denied', 'danger')
        return redirect(url_for('logout'))


#Create executive
@app.route('/CreateExecutive',methods=["GET","POST"])
def createexecutive():
    if session.get('logged_in'):
        if (session.get('userlevel') == 0):
            form = CreateExecutive()
            title = ['Create Executive','Create Executive or Cashier account','']
            if request.method == 'POST' and form.validate():
                username    =   form.username.data
                name        =   form.name.data
                address     =   form.address.data
                phone       =   form.phone.data
                password = sha256_crypt.encrypt(str(form.password.data))
                userlevel   =   form.userlevel.data

                cur = mysql.connection.cursor()
                checkexecutive= cur.execute("select username from userdetail where username = %s ",[username])
                if checkexecutive == False:
                        if(cur.execute('''Insert into userdetail (username, name, address,phone) VALUES (%s, %s, %s, %s)''', (username, name, address,phone)) and cur.execute('''Insert into userstore  (username,password,userlevel,isActive) VALUES (%s, %s, %s,%s)''', (username,password,userlevel,"active"))):
                            mysql.connection.commit()
                            cur.close()
                            flash('Created Successfully!!', 'success')
                            return redirect('CreateExecutive')
                        else:
                            flash('Something went wrong', 'danger')
                            return redirect('CreateExecutive')
                else:
                    flash(f"CreateExecutive account with username - {username} already exists !", "danger")
                    return redirect(url_for('createexecutive'))

            return render_template('createexecutive.html',title=title,form=form)  
        else:
            flash('Session Timeout', 'danger')
            return redirect(url_for('login'))
    else:
        flash('Access Denied', 'danger')
        return redirect(url_for('logout'))


#Custom Error
@app.errorhandler(404)
def page_not_found(e):
    return render_template('pages-404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('pages-500.html'), 500

@app.errorhandler(403)
def page_forbidden(e):
    return render_template('pages-403.html'), 403

if __name__ == "__main__":
    app.secret_key = 'retailBanking'
    app.run(debug = True)

#Developed by Socalled