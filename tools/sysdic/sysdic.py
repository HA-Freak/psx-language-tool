"""usage: python sysdic.py ORIGINAL_jp.dic PROJECT_DIR  -> SYSTEM-DIC GER/ENG/POL/ESP"""
import re,os,sys
sys.stdout.reconfigure(encoding='utf-8')
src=sys.argv[1]; base=sys.argv[2]
# (German, English, Polish, Spanish) - Polish without diacritics (PSX font lacks them)
T={
'Enter':('Bestätigen','Enter','Zatwierdz','Aceptar'),'Select':('Auswählen','Select','Wybierz','Seleccionar'),'Back':('Zurück','Back','Wstecz','Atrás'),'Exit':('Zurück','Back','Wstecz','Atrás'),
'Information':('Informationen','Information','Informacje','Información'),'Options':('Optionen','Options','Opcje','Opciones'),'Display':('Anzeige','Display','Wyswietlanie','Pantalla'),
'Confirm':('Bestätigen','Confirm','Potwierdz','Confirmar'),'Discard':('Löschen','Delete','Usun','Eliminar'),'Capture':('Aufnehmen','Capture','Przechwyc','Capturar'),
'Panel':('Bedienfeld','Control Panel','Panel sterowania','Panel de control'),'ON':('Ein','On','Wl.','Sí'),'OFF':('Aus','Off','Wyl.','No'),'YES':('Ja','Yes','Tak','Sí'),'NO':('Nein','No','Nie','No'),
'OK':('OK','OK','OK','OK'),'CANCEL':('Abbrechen','Cancel','Anuluj','Cancelar'),'CONTINUE':('Fortsetzen','Continue','Kontynuuj','Continuar'),'NEXT':('Weiter','Next','Dalej','Siguiente'),
'PREVIOUS':('Zurück','Previous','Wstecz','Anterior'),'AGREE':('Zustimmen','Agree','Zgadzam sie','Acepto'),'DISAGREE':('Ablehnen','Disagree','Nie zgadzam sie','No acepto'),
'ACCEPT':('Zulassen','Accept','Akceptuj','Aceptar'),'REJECT':('Ablehnen','Reject','Odrzuc','Rechazar'),'SAVE':('Speichern','Save','Zapisz','Guardar'),'DELETE':('Löschen','Delete','Usun','Eliminar'),'HELP':('Hilfe','Help','Pomoc','Ayuda')}
T={k.upper():v for k,v in T.items()}
text=open(src,encoding='utf-8').read()
for idx,name in ((0,'GER'),(1,'ENG'),(2,'POL'),(3,'ESP')):
    def rep(m):
        k=m.group(2)[:-3].upper()
        return m.group(1)+T[k][idx]+m.group(4)
    out,n=re.subn(r'^(\{(\w+)\}\s*=\s*")([^"]*)(";)',rep,text,flags=re.M)
    d=os.path.join(base,f'SYSTEM-DIC {name}'); os.makedirs(d,exist_ok=True)
    open(os.path.join(d,'jp.dic'),'w',encoding='utf-8',newline='').write(out)
    open(os.path.join(d,'path.txt'),'w',encoding='utf-8',newline='').write('hdd0:/__system/dic')
    print(name,n, 'jp left:', bool(re.search(r'[\u3040-\u30ff\u4e00-\u9fff]',out)))
