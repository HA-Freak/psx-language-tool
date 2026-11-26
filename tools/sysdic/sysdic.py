"""usage: python sysdic.py ORIGINAL_jp.dic PROJECT_DIR  -> SYSTEM-DIC GER/ENG/POL"""
import re,os,sys
sys.stdout.reconfigure(encoding='utf-8')
src=sys.argv[1]; base=sys.argv[2]
# (German, English, Polish) - Polish without diacritics (PSX font lacks them)
T={
'Enter':('Bestätigen','Enter','Zatwierdz'),'Select':('Auswählen','Select','Wybierz'),'Back':('Zurück','Back','Wstecz'),'Exit':('Zurück','Back','Wstecz'),
'Information':('Informationen','Information','Informacje'),'Options':('Optionen','Options','Opcje'),'Display':('Anzeige','Display','Wyswietlanie'),
'Confirm':('Bestätigen','Confirm','Potwierdz'),'Discard':('Löschen','Delete','Usun'),'Capture':('Aufnehmen','Capture','Przechwyc'),
'Panel':('Bedienfeld','Control Panel','Panel sterowania'),'ON':('Ein','On','Wl.'),'OFF':('Aus','Off','Wyl.'),'YES':('Ja','Yes','Tak'),'NO':('Nein','No','Nie'),
'OK':('OK','OK','OK'),'CANCEL':('Abbrechen','Cancel','Anuluj'),'CONTINUE':('Fortsetzen','Continue','Kontynuuj'),'NEXT':('Weiter','Next','Dalej'),
'PREVIOUS':('Zurück','Previous','Wstecz'),'AGREE':('Zustimmen','Agree','Zgadzam sie'),'DISAGREE':('Ablehnen','Disagree','Nie zgadzam sie'),
'ACCEPT':('Zulassen','Accept','Akceptuj'),'REJECT':('Ablehnen','Reject','Odrzuc'),'SAVE':('Speichern','Save','Zapisz'),'DELETE':('Löschen','Delete','Usun'),'HELP':('Hilfe','Help','Pomoc')}
T={k.upper():v for k,v in T.items()}
text=open(src,encoding='utf-8').read()
for idx,name in ((0,'GER'),(1,'ENG'),(2,'POL')):
    def rep(m):
        k=m.group(2)[:-3].upper()
        return m.group(1)+T[k][idx]+m.group(4)
    out,n=re.subn(r'^(\{(\w+)\}\s*=\s*")([^"]*)(";)',rep,text,flags=re.M)
    d=os.path.join(base,f'SYSTEM-DIC {name}'); os.makedirs(d,exist_ok=True)
    open(os.path.join(d,'jp.dic'),'w',encoding='utf-8',newline='').write(out)
    open(os.path.join(d,'path.txt'),'w',encoding='utf-8',newline='').write('hdd0:/__system/dic')
    print(name,n, 'jp left:', bool(re.search(r'[\u3040-\u30ff\u4e00-\u9fff]',out)))
