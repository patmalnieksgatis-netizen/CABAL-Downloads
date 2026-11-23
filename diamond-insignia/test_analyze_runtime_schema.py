from analyze_runtime_schema import analyze

def test_grouping():
    report={'mode':'READ_ONLY','sql_mutations':False,
            'game':{'world_inner_pid':64516,'game_modules':[{'name':'WorldSvr_01_01','sha256':'a','has_diamond_literal':False}]},
            'database':{'status':'SERVER01_METADATA_READ','row_count':3,'limited_to_first':140,
                'columns':[{'schema':'dbo','table':'MeritPower','column':'CharacterIdx','data_type':'int'},
                           {'schema':'dbo','table':'MeritPower','column':'MeritScore','data_type':'bigint'},
                           {'schema':'dbo','table':'Other','column':'MasteryRank','data_type':'tinyint'}]}}
    out=analyze(report)
    assert out['table_count']==2
    assert out['returned_rows']==3
    assert out['source_status']=='SERVER01_METADATA_READ'
    assert out['diamond_persistence_proven'] is False
    assert out['could_be_truncated'] is False
    assert out['loaded_game_modules'][0]['name']=='WorldSvr_01_01'
    assert [t['table'] for t in out['tables']] == ['MeritPower', 'Other']

def test_safety():
    try:
        analyze({'mode':'READ_ONLY','sql_mutations':True})
    except ValueError:
        return
    raise AssertionError('unsafe data accepted')

if __name__ == '__main__':
    test_grouping();test_safety();print('PASS_SCHEMA_REPORT_ANALYZER')
