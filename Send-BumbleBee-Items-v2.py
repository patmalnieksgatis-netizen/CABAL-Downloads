"""Grant the six requested items once through the existing native GM mail.

All current option/upgrade tables are read in this invocation before SQL writes.
No separate read/report round trip, inventory edits, level changes or restart.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

VM_UUID='7632fb78-37a0-f645-97c0-dc322c50b002'
WORLD_SHA='caec7772acd22fd8918cfac386845c644451781e48c51975eaefed334c6705c3'
SQL_BASE64='U0VUIE5PQ09VTlQgT047ClNFVCBYQUNUX0FCT1JUIE9OOwpTRVQgTE9DS19USU1FT1VUIDUwMDA7CklGIERCX05BTUUoKTw+TidTZXJ2ZXIwMScgVEhST1cgNTEwMDAsJ1dST05HX0dBTUVfREFUQUJBU0U7IE5PVEhJTkdfU0VOVCcsMTsKREVDTEFSRSBAaXRlbXMgVEFCTEUoTiBpbnQgUFJJTUFSWSBLRVksS2luZCBiaWdpbnQsT3B0IGJpZ2ludCxMYWJlbCB2YXJjaGFyKDQwKSk7CklOU0VSVCBAaXRlbXMgVkFMVUVTCl9fSVRFTV9WQUxVRVNfXzsKQkVHSU4gVFJZCiBCRUdJTiBUUkFOU0FDVElPTjsKIERFQ0xBUkUgQGxvY2sgaW50OwogRVhFQyBAbG9jaz1zeXMuc3BfZ2V0YXBwbG9jayBAUmVzb3VyY2U9J0NsaWVudDI5MV9CdW1ibGVCZWVGdWxsSXRlbXNfMjAyNjExMTM6QnVtYmxlQmVlJywKICBATG9ja01vZGU9J0V4Y2x1c2l2ZScsQExvY2tPd25lcj0nVHJhbnNhY3Rpb24nLEBMb2NrVGltZW91dD01MDAwOwogSUYgQGxvY2sgSVMgTlVMTCBPUiBAbG9jazwwIFRIUk9XIDUxMDAwLCdCVU1CTEVCRUVfTUFJTF9MT0NLX0ZBSUxFRCcsMTsKIERFQ0xBUkUgQHVzZXIgaW50LEBjaGFyYWN0ZXIgaW50LEBtYXRjaGVzIGludDsKIFNFTEVDVCBAY2hhcmFjdGVyPU1JTihDaGFyYWN0ZXJJZHgpLEBtYXRjaGVzPUNPVU5UKCopIEZST00gZGJvLmNhYmFsX2NoYXJhY3Rlcl90YWJsZSBXSVRIKFVQRExPQ0ssSE9MRExPQ0spCiAgV0hFUkUgTmFtZSBDT0xMQVRFIExhdGluMV9HZW5lcmFsXzEwMF9CSU4yPSdCdW1ibGVCZWUnOwogSUYgQG1hdGNoZXM8PjEgT1IgQGNoYXJhY3RlciBJUyBOVUxMIFRIUk9XIDUxMDAxLCdCVU1CTEVCRUVfQ0hBUkFDVEVSX0lERU5USVRZX01JU01BVENIOyBOT1RISU5HX1NFTlQnLDE7CiBTRVQgQHVzZXI9QGNoYXJhY3Rlci8xNjsKIElGIE5PVCBFWElTVFMoU0VMRUNUIDEgRlJPTSBBY2NvdW50LmRiby5jYWJhbF9hdXRoX3RhYmxlIFdIRVJFIFVzZXJOdW09QHVzZXIpCiAgVEhST1cgNTEwMDEsJ0JVTUJMRUJFRV9BQ0NPVU5UX05PVF9GT1VORDsgTk9USElOR19TRU5UJywxOwogSUYgTk9UIEVYSVNUUyhTRUxFQ1QgMSBGUk9NIHN5cy5wYXJhbWV0ZXJzIFdIRVJFIG9iamVjdF9pZD1PQkpFQ1RfSUQoJ2Riby5jYWJhbF90b29sX21haWxfc2VuZCcpCiAgQU5EIG5hbWU9J0BJdGVtS2luZElkeCcgQU5EIFRZUEVfTkFNRSh1c2VyX3R5cGVfaWQpPSdiaWdpbnQnKQogIFRIUk9XIDUxMDAxLCdOQVRJVkVfTUFJTF9JVEVNX0tJTkRfTk9UX0JJR0lOVDsgTk9USElOR19TRU5UJywxOwogSUYgSEFTSEJZVEVTKCdTSEEyXzI1NicsQ09OVkVSVCh2YXJiaW5hcnkobWF4KSxPQkpFQ1RfREVGSU5JVElPTihPQkpFQ1RfSUQoJ2Riby5jYWJhbF90b29sX21haWxfc2VuZCcpKSkpIElTIE5VTEwKICBPUiBIQVNIQllURVMoJ1NIQTJfMjU2JyxDT05WRVJUKHZhcmJpbmFyeShtYXgpLE9CSkVDVF9ERUZJTklUSU9OKE9CSkVDVF9JRCgnZGJvLmNhYmFsX3Rvb2xfbWFpbF9zZW5kJykpKSk8PgogIDB4RTFBQ0EyNDBDRjUwQzU1QzY4NDdBMzhDMjAyQTc5NzEyREZDNUUzRUMzMTQ4MEZENjdCNDc5QTk5MTExRTAyOQogIE9SIEhBU0hCWVRFUygnU0hBMl8yNTYnLENPTlZFUlQodmFyYmluYXJ5KG1heCksT0JKRUNUX0RFRklOSVRJT04oT0JKRUNUX0lEKCdkYm8uTWFpbF9HZXRHTVR5cGUnKSkpKSBJUyBOVUxMCiAgT1IgSEFTSEJZVEVTKCdTSEEyXzI1NicsQ09OVkVSVCh2YXJiaW5hcnkobWF4KSxPQkpFQ1RfREVGSU5JVElPTihPQkpFQ1RfSUQoJ2Riby5NYWlsX0dldEdNVHlwZScpKSkpPD4KICAweEYxMUE3RUY4NzNFNTdBQ0M2RkM5RDVERERCQjcwOTNFMkU1Mzc0NUYzNURBNTExNjU5MDE1ODM3RDBEQ0M0RTEKICBUSFJPVyA1MTAwMiwnTkFUSVZFX01BSUxfSEVMUEVSX0NIQU5HRUQ7IE5PVEhJTkdfU0VOVCcsMTsKIElGIE9CSkVDVF9JRCgnZGJvLkNsaWVudDI5MV9CdW1ibGVCZWVGdWxsSXRlbXNfMjAyNjExMTMnLCdVJykgSVMgTlVMTAogIENSRUFURSBUQUJMRSBkYm8uQ2xpZW50MjkxX0J1bWJsZUJlZUZ1bGxJdGVtc18yMDI2MTExMygKICAgQ2hhcmFjdGVySWR4IGludCBOT1QgTlVMTCxOIGludCBOT1QgTlVMTCxLaW5kIGJpZ2ludCBOT1QgTlVMTCxPcHQgYmlnaW50IE5PVCBOVUxMLAogICBNYWlsSUQgaW50IE5PVCBOVUxMLFNlbnRBdCBkYXRldGltZTIgTk9UIE5VTEwgREVGQVVMVCBTWVNVVENEQVRFVElNRSgpLAogICBQUklNQVJZIEtFWShDaGFyYWN0ZXJJZHgsTikpOwogSUYgRVhJU1RTKFNFTEVDVCAxIEZST00gZGJvLkNsaWVudDI5MV9CdW1ibGVCZWVGdWxsSXRlbXNfMjAyNjExMTMgV0lUSChVUERMT0NLLEhPTERMT0NLKSBXSEVSRSBDaGFyYWN0ZXJJZHg9QGNoYXJhY3RlcikKIEJFR0lOCiAgSUYgKFNFTEVDVCBDT1VOVCgqKSBGUk9NIGRiby5DbGllbnQyOTFfQnVtYmxlQmVlRnVsbEl0ZW1zXzIwMjYxMTEzIFdIRVJFIENoYXJhY3RlcklkeD1AY2hhcmFjdGVyKTw+NgogICBPUiBFWElTVFMoU0VMRUNUIE4sS2luZCxPcHQgRlJPTSBAaXRlbXMgRVhDRVBUCiAgIFNFTEVDVCBOLEtpbmQsT3B0IEZST00gZGJvLkNsaWVudDI5MV9CdW1ibGVCZWVGdWxsSXRlbXNfMjAyNjExMTMgV0hFUkUgQ2hhcmFjdGVySWR4PUBjaGFyYWN0ZXIpCiAgIFRIUk9XIDUxMDAzLCdNQUlMX0dSQU5UX0pPVVJOQUxfRElGRkVSUzsgTk9USElOR19TRU5UJywxOwogIENPTU1JVDsKICBQUklOVCAnQlVNQkxFQkVFX0ZVTExfSVRFTVNfQUxSRUFEWV9TRU5UOyBOT19EVVBMSUNBVEVTJzsKICBSRVRVUk47CiBFTkQ7CiBERUNMQVJFIEBuIGludD0xLEBraW5kIGJpZ2ludCxAb3B0IGJpZ2ludCxAbGFiZWwgdmFyY2hhcig0MCksQGJvZHkgdmFyY2hhcig1MTIpLEBpZCBpbnQ7CiBERUNMQVJFIEByZXN1bHQgVEFCTEUoSUQgaW50KTsKIFdISUxFIEBuPD02CiBCRUdJTgogIFNFTEVDVCBAa2luZD1LaW5kLEBvcHQ9T3B0LEBsYWJlbD1MYWJlbCBGUk9NIEBpdGVtcyBXSEVSRSBOPUBuOwogIFNFVCBAYm9keT0nQnVtYmxlQmVlIHJlcXVlc3RlZCB0ZXN0IGVxdWlwbWVudC4gUGVybWFuZW50IGF0dGFjaG1lbnQ6ICcrQGxhYmVsOwogIERFTEVURSBAcmVzdWx0OwogIElOU0VSVCBAcmVzdWx0IEVYRUMgZGJvLmNhYmFsX3Rvb2xfbWFpbF9zZW5kCiAgIEBTZW5kZXJOYW1lPSdHTScsQFJlY2VpdmVyQ2hhcklkeD1AY2hhcmFjdGVyLEBUaXRsZT1AbGFiZWwsQENvbnRlbnQ9QGJvZHksCiAgIEBBbHo9MCxASXRlbUtpbmRJZHg9QGtpbmQsQEl0ZW1PcHRpb249QG9wdCxASXRlbUR1cmF0aW9uSWR4PTAsQEV4cGlyYXRpb25UaW1lPU5VTEw7CiAgSUYgKFNFTEVDVCBDT1VOVCgqKSBGUk9NIEByZXN1bHQpPD4xIFRIUk9XIDUxMDA0LCdNQUlMX1JFQ0VJUFRfRkFJTEVEJywxOwogIFNFTEVDVCBAaWQ9SUQgRlJPTSBAcmVzdWx0OwogIElGIEBpZCBJUyBOVUxMIE9SIEBpZDw9MCBPUiBOT1QgRVhJU1RTKFNFTEVDVCAxIEZST00gZGJvLmNhYmFsX21haWxfcmVjZWl2ZWRfdGFibGUKICAgV0hFUkUgUmVjZWl2ZXJDaGFySWR4PUBjaGFyYWN0ZXIgQU5EIFJlY2VpdmVkTWFpbElEPUBpZCBBTkQgSXNDb21taXR0ZWQ9MSBBTkQgVHlwZT00CiAgIEFORCBJdGVtS2luZElkeD1Aa2luZCBBTkQgSXRlbU9wdGlvbj1Ab3B0IEFORCBJdGVtRHVyYXRpb25JZHg9MAogICBBTkQgRXhwaXJhdGlvblRpbWUgSVMgTlVMTCBBTkQgU2VuZGVyTmFtZT0nR00nIEFORCBBbHo9MCBBTkQgSXNSZWNlaXZlZEl0ZW09MCkKICAgVEhST1cgNTEwMDUsJ01BSUxfQVRUQUNITUVOVF9QT1NUQ0hFQ0tfRkFJTEVEJywxOwogIElOU0VSVCBkYm8uQ2xpZW50MjkxX0J1bWJsZUJlZUZ1bGxJdGVtc18yMDI2MTExMyhDaGFyYWN0ZXJJZHgsTixLaW5kLE9wdCxNYWlsSUQpCiAgIFZBTFVFUyhAY2hhcmFjdGVyLEBuLEBraW5kLEBvcHQsQGlkKTsKICBTRVQgQG4rPTE7CiBFTkQ7CiBDT01NSVQ7CiBQUklOVCAnQlVNQkxFQkVFX0ZVTExfSVRFTVNfU0VOVDsgTUFJTFM2OyBPUEVOX01BSUxfQU5EX0NMQUlNX0FUVEFDSE1FTlRTJzsKIFNFTEVDVCBDT05DQVQoJ0JVTUJMRUJFRV9JVEVNPScsai5OLCc7ICcsaS5MYWJlbCwnOyBNQUlMX0lEPScsai5NYWlsSUQpIEZST00gZGJvLkNsaWVudDI5MV9CdW1ibGVCZWVGdWxsSXRlbXNfMjAyNjExMTMgagogSk9JTiBAaXRlbXMgaSBPTiBpLk49ai5OIFdIRVJFIGouQ2hhcmFjdGVySWR4PUBjaGFyYWN0ZXIgT1JERVIgQlkgai5OOwpFTkQgVFJZCkJFR0lOIENBVENICiBJRiBAQFRSQU5DT1VOVD4wIFJPTExCQUNLOwogVEhST1c7CkVORCBDQVRDSDsK'
PINS={'Item.scp': 'b8b79a3caef7b48d56c1604d51c98be1497e63167916bb3a6f0286218eae6750', 'Item2.scp': '0c91422986344bd533be8edd701afb77e70b158a3cfbf39094f9fad0ca94c669', 'Item3.scp': 'fd09784bc4a582c376a4befa5ef6a7c8f652e68294081da2bafb77559cfb7b80', 'Item4.scp': 'ef57aaea1f793aecf388f1b209ac80ffb1ccd8e321f6eefcae79c3cdad92d009', 'Forcecore_Option.scp': 'c756d28f004838b6193078d76c30b809bd1231dfcea91fb19252d8f6c3139db6', 'DivineUpgrade.scp': '019b3ed7dc05fc0a28b17c0d759e3768f85fa5f35d84c17a13a491bb454e930f', 'Enchant.scp': '7710a53ab9dc76ea392fd10e073ad0d6c1703a52a8894590ba0fca15515c0db6'}
ENUMS={}


def need(value,code):
    if not value:raise RuntimeError(code)


def run(args,data=None,timeout=30):
    p=subprocess.run(args,input=data,capture_output=True,timeout=timeout)
    need(p.returncode==0,'COMMAND_READ_FAILED_'+args[0])
    return p.stdout


def sections(body):
    """SCP has an implicit row number before the explicitly named columns."""
    out={};name=None;columns=[]
    for line in body.decode('cp949',errors='replace').splitlines():
        if line.startswith('['):
            cells=line.split();name=cells[0][1:-1];columns=cells[1:];out[name]=[]
        elif name and line.strip() and line.split()[0].isdigit():
            cells=line.split()
            need(len(cells)>=len(columns)+1,'SHORT_SCP_ROW_'+name)
            row=dict(zip(columns,cells[1:]));row['_row']=cells[0];out[name].append(row)
    return out


def number(value):
    if value in ENUMS:return ENUMS[value]
    return int(value,16 if value.lower().startswith('0x') else 10)


def field(row,*aliases):
    normalize=lambda s:re.sub('[^a-z0-9]','',s.lower())
    keys={normalize(k):v for k,v in row.items()}
    for name in aliases:
        if normalize(name) in keys:return number(keys[normalize(name)])
    raise RuntimeError('SCP_REQUIRED_COLUMN_MISSING_'+aliases[0])


def chaos_for(chaos,kind,level):
    matches=[r for r in chaos.get('ChaosUpgrade_ItemList',[]) if field(r,'ChaosItem_Index')==kind]
    need(len(matches)==1,'CHAOS_ITEM_NOT_UNIQUE_'+str(kind))
    group=field(matches[0],'ChaosItem_Group')
    rows=[r for r in chaos.get('ChaosUpgrade_Value',[])
          if field(r,'ChaosItem_Group')==group and field(r,'ChaosItem_Level')==level]
    need(rows,'CHAOS_LEVEL_HAS_NO_BONUSES_'+str(kind)+'_'+str(level))
    values={field(r,'ChaosItem_ForceID'):field(r,'ChaosItem_ForceValue') for r in rows}
    need(any(k>0 and v>0 for k,v in values.items()),'CHAOS_LEVEL_HAS_NO_POSITIVE_BONUSES_'+str(kind))
    return values


def recipe(files):
    itemrows=[]
    ENUMS.clear()
    for name in ('Item.scp','Item2.scp','Item3.scp','Item4.scp'):
        for token,value in re.findall(rb'(?m)^(@IDT_[A-Za-z0-9_]+)\s*=\s*(-?\d+)',files[name]):
            key=token.decode('ascii');value=int(value)
            need(key not in ENUMS or ENUMS[key]==value,'ITEM_TYPE_ENUM_CONFLICT')
            ENUMS[key]=value
        itemrows+=sections(files[name]).get('Item',[])
    items={int(r['Index']):r for r in itemrows}
    chaos=sections(files['Chaos_Upgrade.scp'])
    # Resolve Sage from its actual Magic Attack bonus, rather than guessing the
    # order of the three adjacent belt IDs (Sage/Fighter/Chaos).
    belts=[]
    for kind in (33554729,33554730,33554731):
        try:force=chaos_for(chaos,kind,20)
        except RuntimeError:continue
        if force.get(4,0)>0 and force.get(3,0)==0:belts.append(kind)
    need(len(belts)==1,'SAGE_BELT_MAGIC_PROFILE_NOT_UNIQUE')
    belt=belts[0]
    need(items[belt]['Type']=='@IDT_BELT','SAGE_BELT_TYPE_MISMATCH')
    carnelian=33555377
    need(items[carnelian]['Type']=='@IDT_CARN','CARNELIAN_TYPE_MISMATCH')
    chaos_for(chaos,carnelian,20)
    force=sections(files['Forcecore_Option.scp'])
    result=[]
    for kind,grade,label in ((33558050,1,'Crest Life 3S HP DEF CDI'),
                              (33558051,3,'Crest Sky 3S HP DEF CDI'),
                              (33558052,2,'Crest Earth 3S HP DEF CDI')):
        need(items[kind]['Type']=='@IDT_AVAN' and int(items[kind]['Grade'])==grade,
             'CREST_PROFILE_CHANGED')
        column='Costume'+str(grade)
        codes=[]
        for force_id in (1,5,8):
            rows=[r for r in force['Option'] if int(r[column+'Lnk'])==force_id]
            need(len(rows)==1,'CREST_FORCE_CODE_NOT_UNIQUE')
            code=int(rows[0]['_row']);need(0<code<16,'CREST_OPTION_CODE_RANGE')
            values=[r for r in force['CoreLink_Etc']
                    if int(r['CoreNum'])==1 and int(r['OptCodeLnk'])==force_id]
            need(len(values)==1 and int(values[0][column])>0,'CREST_FORCE_BONUS_MISSING')
            codes.append(code)
        option=(3<<28)|(codes[0]<<24)|((16|codes[1])<<16)|((16|codes[2])<<8)
        result.append((kind,option,label))
    result.extend(((belt|(20<<13),0,'Sage Belt Chaos +20'),
                   (carnelian|(20<<13),0,'Carnelian Chaos +20')))
    bike=33556579
    need(items[bike]['Type']=='@IDT_BIKE' and int(items[bike]['Grade'])==14,'QW7_PROFILE_CHANGED')
    divine=sections(files['DivineUpgrade.scp'])
    groups=[r for r in divine['Divine_UpGrade_Main'] if field(r,'Item_type')==22 and field(r,'Item_grade')==14]
    need(len(groups)==1,'BIKE_DIVINE_GROUP_NOT_UNIQUE')
    group=field(groups[0],'Divine_Upgrade_Group')
    need(any(field(r,'Divine_Upgrade_Group')==group and field(r,'Divine_Upgrade_level')==15
             and field(r,'Force_Value')>0 for r in divine['Divine_UpGrade_Value']),
         'BIKE_DIVINE_15_BONUSES_MISSING')
    extreme=sections(files['Limit_Upgrade.scp'])
    base=[r for r in extreme.get('Limit_Upgrade_Base',[])
          if field(r,'Item_Type')==22 and field(r,'Item_Grade','Item_grade','Grade')==14]
    need(len(base)==1,'BIKE_EXTREME_GROUP_NOT_UNIQUE')
    group=field(base[0],'Limit_Upgrade_Group')
    maximum=field(base[0],'Limit_Upgrade_Max')
    need(maximum>=6,'BIKE_EXTREME_6_ABOVE_NATIVE_MAX_'+str(maximum))
    levels=[r for r in extreme.get('Limit_Upgrade_Main',[])
            if field(r,'Limit_Upgrade_Group')==group and field(r,'Limit_Upgrade_Level')==6]
    need(levels,'BIKE_EXTREME_6_MAIN_ENTRY_MISSING')
    options={field(r,'Limit_Upgrade_Option') for r in levels}
    values=[r for r in extreme.get('Limit_Upgrade_Value',[])
            if field(r,'Limit_Upgrade_Option') in options]
    need(values and any(field(r,'Force_Value')>0 for r in values),
         'BIKE_EXTREME_6_BONUSES_MISSING')
    ench=sections(files['Enchant.scp'])
    limits=[r for r in ench['EnchantExtendLimit'] if field(r,'ItemGrade')==14]
    need(len(limits)==1 and field(limits[0],'MaxEnchant')>=20,'BIKE_NORMAL_20_ABOVE_NATIVE_MAX')
    kind=bike|(20<<13)|(6<<32)|(15<<36)
    result.append((kind,3<<28,'QW7 +20 3S EXT6 DIV15'))
    need(len(result)==6 and all(0<k<2**63 and 0<=o<2**63 for k,o,_ in result),'INVALID_RECIPE')
    return result


def decode(raw):
    if raw.startswith((b'\xff\xfe',b'\xfe\xff')):return raw.decode('utf-16',errors='replace')
    if b'\0' in raw[:100]:return raw.decode('utf-16-le',errors='replace')
    return raw.decode('utf-8-sig',errors='replace')


def main():
    need(sys.argv[1:]==['--apply'],'EXPLICIT_APPLY_REQUIRED')
    need(os.geteuid()==0 and Path('/sys/class/dmi/id/product_uuid').read_text().strip().lower()==VM_UUID,
         'WRONG_TEST_VM_OR_ROOT_REQUIRED')
    pid=run(['docker','exec','cabal_main','supervisorctl','pid','WorldSvr_01_01']).decode().strip()
    need(pid.isdigit() and int(pid)>0,'WORLD_NOT_RUNNING')
    image=run(['docker','exec','cabal_main','cat','/proc/'+pid+'/exe'])
    need(hashlib.sha256(image).hexdigest()==WORLD_SHA,'WORLD_PROFILE_CHANGED')
    files={}
    for name in list(PINS)+['Chaos_Upgrade.scp','Limit_Upgrade.scp']:
        body=run(['docker','exec','cabal_main','cat','/etc/cabal/Data/'+name])
        need(0<len(body)<=3*1024**2,'GAME_FILE_SIZE_'+name)
        if name in PINS:need(hashlib.sha256(body).hexdigest()==PINS[name],'GAME_FILE_CHANGED_'+name)
        files[name]=body
    rows=recipe(files)
    for i,(kind,option,label) in enumerate(rows,1):
        print('BUMBLEBEE_ITEM='+str(i)+'; '+label+'; KIND='+str(kind)+'; OPT='+str(option),flush=True)
    sql=base64.b64decode(SQL_BASE64).decode('ascii')
    values=',\n'.join(' ('+str(i)+','+str(kind)+','+str(option)+",'"+label+"')"
                       for i,(kind,option,label) in enumerate(rows,1))
    need(sql.count('__ITEM_VALUES__')==1,'MAIL_TEMPLATE_INVALID')
    sql=sql.replace('__ITEM_VALUES__',values)
    shell='''set +x
export SQLCMDPASSWORD="${MSSQL_SA_PASSWORD:-${SA_PASSWORD:-}}"
[ -n "$SQLCMDPASSWORD" ] || exit 2
tool=/opt/mssql-tools18/bin/sqlcmd
[ -x "$tool" ] || tool=/opt/mssql-tools/bin/sqlcmd
exec "$tool" -S localhost -U sa -N -C -d Server01 -b -l 5 -t 30 -h -1 -W -w 65535 -i /dev/stdin
'''
    p=subprocess.run(['docker','exec','-i','sql_main','sh','-ec',shell],input=sql.encode('ascii'),capture_output=True,timeout=50)
    text=decode(p.stdout+p.stderr)
    for line in text.splitlines():
        if line.startswith(('BUMBLEBEE_','Msg ')) or any(s in line for s in ('NOTHING_SENT','MISMATCH','FAILED','DIFFERS','Invalid column','Invalid object')):
            print(line[:500],flush=True)
    need(p.returncode==0 and any(s in text for s in ('BUMBLEBEE_FULL_ITEMS_SENT;','BUMBLEBEE_FULL_ITEMS_ALREADY_SENT;')),
         'DELIVERY_NOT_CONFIRMED; KEEP_OUTPUT; DO_NOT_CHANGE_REQUEST_ID')
    print('BUMBLEBEE_SIX_ITEMS_CONFIRMED; OPEN_MAIL_AND_CLAIM; NO_SERVICE_RESTART',flush=True)


if __name__=='__main__':
    try:main()
    except Exception as e:
        print('BUMBLEBEE_STOPPED; '+str(e),flush=True)
        raise SystemExit(1)
