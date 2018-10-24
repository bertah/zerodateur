import re
import logging
from robobrowser import RoboBrowser

class FDTParser():
	# Event Punch   État
	# 1   	IN		1	Arrivée
	# 10  	OUT		10	Arrêt temporaire
	# 	  	IN			Retour arrêt temporaire
	# 20  	OUT		20	Lunch
	# 30  	IN 		1	Retour du repas
	# 60  	OUT   	60	Quitter
	
	def __init__(self, company, username, password, simulation=False):
		self.company = company
		self.username = username
		self.password = password 
		self.log = logging.getLogger()
		self.br = ""
		self.simulation = simulation
				
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
		# todo detect if already logged in
		self.login()
		
		self.br.open('https://www.fdtpro.com/fdtpro_v6_00_00/main.php')
		scr = self.br.find('script')
		p = re.compile(r'var current_state=(?P<state>\d+)')
		m = p.search(str(scr))
		state = m.group('state')
		p = re.compile(r'var repas_was_used=(?P<repas>\d)')
		m = p.search(str(scr))
		repas = m.group('repas')
		
		if repas == '1' and state == '1':
			state = '30'
		
		return state
		
	def punchInDayStart(self):
		self.submitEvent('1')
	
	def punchOutLunch(self):
		self.submitEvent('20')
	
	def punchInBackFromLunch(self):
		self.submitEvent('30')
	
	def punchOutDayEnd(self):
		self.submitEvent('60')
		
	def submitEvent(self, state_id):
		if not self.simulation:
			state = state_id.replace('but_','')
			self.br.open(url='https://www.fdtpro.com/fdtpro_v6_00_00/custom_ccq_horo_change_state.php?evtget=' + state, method='post', headers={'Content-type': 'application/x-www-form-urlencoded', 'Origin': 'https://www.fdtpro.com', 'Referer': 'https://www.fdtpro.com/fdtpro_v5_03_00/custom_ccq_horo.php'})
			self.log.debug(self.br.response)
		