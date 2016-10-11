from robobrowser import RoboBrowser

class FDTParser():
	
	def __init__(self, company, username, password):
		self.company = company
		self.username = username
		self.password = password 
		self.log = logging.getLogger()
				
	def login(self):
		if not self.br :
			br = RoboBrowser(user_agent='Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko', parser='html.parser')
			self.br = br
		
		self.br.open('https://www.fdtpro.com/login.php?lang=fr')
		login_form = self.br.get_form('login_from')
		login_form['fcompany'].value = self.company
		login_form['fusername'].value = self.username
		login_form['fpassword'].value = self.password
		
		self.br.submit_form(login_form)
		
	def getCurrentState(self):
		self.br.open('https://www.fdtpro.com/fdtpro_v5_03_00/main.php')
		scr = self.br.find('script')
		p = re.compile(r'var current_state=(?P<state>\d+)')
		m = p.search(str(scr))
		state = m.group('state')
		return state
		
	def punchInDayStart(self):
		but_id = 'but_1'
	
	def punchOutLunch(self):
		but_id = 'but_20'
	
	def punchInBackFromLunch(self):
		but_id = 'but_30'
	
	def punchOutDayEnd(self):
		but_id = 'but_60'
		
	def submitEvent(but_id);
		self.br.open('https://www.fdtpro.com/fdtpro_v5_03_00/main.php')
		
		#xmlhttpKeepAlive.open("POST","custom_ccq_horokeepalive.php",true);
		#xmlhttpKeepAlive.setRequestHeader("Content-type","application/x-www-form-urlencoded");  
		#xmlhttpKeepAlive.send('currentstate='+current_state);