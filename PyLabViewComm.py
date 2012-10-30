import time
import _winreg as winreg

key = winreg.CreateKey(winreg.HKEY_CURRENT_USER,"PyLabView")

#winreg.SetValue(winreg.HKEY_CURRENT_USER,"Test\test",winreg.REG_SZ,"Running")
tid = time.time()
for i in range(0,100000):
	winreg.SetValueEx(key,"rtd_temperature",0,winreg.REG_SZ,str(i))
	winreg.QueryValue(winreg.HKEY_CURRENT_USER,"PyLabView")

print time.time() - tid
	
#print winreg.QueryValue(winreg.HKEY_CURRENT_USER,"PyLabView")
#a = winreg.QueryValueEx(key,"rtd_temperature")
#print a[0]
#print winreg.QueryInfoKey(key)
#print winreg.QueryValue(key,'My String')
#print sid
#print key
