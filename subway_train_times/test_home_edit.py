"""Offline acceptance tests for the shared-home board. No live writes/network."""
import io
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw
import subway_server as server
import home_edit

REAL_GET_AIR_QUALITY = server.get_air_quality

WEATHER = {
    'current': {'temperature_2m':53, 'apparent_temperature':47, 'weather_code':0},
    'daily': {'time':['2026-11-08','2026-11-09'], 'temperature_2m_max':[61,56],
              'temperature_2m_min':[46,43], 'precipitation_probability_max':[17,4],
              'sunrise':['2026-11-08T06:34','2026-11-09T06:35'],
              'sunset':['2026-11-08T16:44','2026-11-09T16:43']}}
NOW = datetime(2026,11,8,18,0)

class HomeEditTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state=Path(self.tmp.name)
        self.patches=[patch.object(server,'load_config',return_value={}),
                      patch.object(server.overlay_store,'OVERLAY_FILE',self.state/'overlays.json'),
                      patch.object(server.overlay_store,'IMAGE_DIR',self.state/'images'),
                      patch.object(server,'get_air_quality',return_value=25)]
        for p in self.patches: p.start(); self.addCleanup(p.stop)

    def test_refresh_is_fifteen_minutes_even_with_old_config(self):
        with patch.object(server,'load_config',return_value={'refresh_rate':{'intervals':{'fast':60,'slow':1800,'night':1800}}}):
            self.assertEqual(server.calculate_refresh_rate(),900)
            c=server.app.test_client()
            self.assertEqual(c.get('/refresh-rate').json['refresh_minutes'],15)
            self.assertEqual(c.get('/status').json['layout'],'home_edit')
            self.assertEqual(c.get('/status').json['renderer_version'],'home-edit-2-reminder-list')

    def test_no_transit_requests_and_real_weather_fields(self):
        with patch.object(server,'get_subway',side_effect=AssertionError('Transit must not be requested'),create=True):
            image=server.generate_image(now=NOW,weather=WEATHER)
        self.assertEqual(image.size,(800,480))
        image.save(self.state/'normal.png')

    def test_missing_sparse_and_extreme_weather(self):
        for w in [{}, {'current':{}}, {'current':{'temperature_2m':-12,'apparent_temperature':-30,'weather_code':95}}, {'daily':{'time':[]}}]:
            self.assertEqual(server.generate_image(now=NOW,weather=w).size,(800,480))

    def test_footer_selects_tomorrow_by_date_not_position(self):
        self.assertEqual(home_edit.forecast_index(WEATHER,NOW),1)
        self.assertIsNone(home_edit.forecast_index(WEATHER,datetime(2026,11,12)))

    def test_long_overlay_is_ellipsized_and_slots_do_not_crash(self):
        for slot in ['banner','sidebar','fullscreen']:
            o={'id':'test','slot':slot,'title':'A very long reminder title '*5,'text':'Very long household reminder '*40}
            im=home_edit.render(NOW,WEATHER,25)
            home_edit.draw_overlay(im,o)
            self.assertEqual(im.size,(800,480))

    def test_reminder_layout_empty_single_multiple_overflow_and_long_text(self):
        fixtures = {
            'empty': [],
            'single': [{'id':'one','title':'Household','text':'A quiet note'}],
            'multiple': [{'id':f'n{i}','title':f'Note {i}','text':f'Text {i}', 'priority':4-i} for i in range(3)],
            'overflow': [{'id':f'n{i}','title':f'Note {i}','text':'A long note ' * 18, 'priority':10-i} for i in range(9)],
        }
        for label, reminders in fixtures.items():
            with self.subTest(label=label):
                im=home_edit.render(NOW, WEATHER, 25, reminders=reminders)
                native=im.convert('1')
                self.assertEqual(native.size,(800,480))
                self.assertEqual(native.mode,'1')
                colors=native.getcolors(800*480)
                self.assertIsNotNone(colors)
                self.assertEqual(len(colors or []), 2)
                if label == 'overflow':
                    with patch.object(home_edit, '_text', wraps=home_edit._text) as text:
                        home_edit.draw_reminder_list(im, reminders)
                    self.assertTrue(any(call.args[3] == '+5 more' for call in text.call_args_list))
                    park = im.convert('1').crop((423, 294, 766, 343))
                    self.assertGreater(park.histogram()[0], 0)
        long_title=[{'id':'long','title':'Extraordinarily long title '*8,'text':'unbroken-'*40}]
        self.assertEqual(home_edit.render(NOW, WEATHER, reminders=long_title).size,(800,480))

    def test_active_reminders_merge_by_priority_and_fullscreen_stays_exclusive(self):
        low={'id':'banner-low','slot':'banner','title':'Low','text':'Later','priority':1,'created_at':'2026-11-08T10:00:00'}
        high={'id':'sidebar-high','slot':'sidebar','title':'High','text':'First','priority':9,'created_at':'2026-11-08T09:00:00'}
        mid={'id':'banner-mid','slot':'banner','title':'Mid','text':'Second','priority':5,'created_at':'2026-11-08T11:00:00'}
        img=Image.new('L',(800,480),255)
        with patch.object(server.overlay_store,'active',side_effect=lambda slot=None: {'fullscreen':[], 'sidebar':[high], 'banner':[mid,low], None:[high,mid,low]}[slot]) as active, patch.object(home_edit,'draw_reminder_list') as draw_list:
            server.apply_overlays(img, ImageDraw.Draw(img))
        ordered=draw_list.call_args.args[1]
        self.assertEqual([o['id'] for o in ordered],['sidebar-high','banner-mid','banner-low'])
        fullscreen={'id':'special','slot':'fullscreen','title':'Special','text':'One card'}
        with patch.object(server.overlay_store,'active',side_effect=lambda slot=None: [fullscreen] if slot=='fullscreen' else [high,mid,low]), patch.object(server,'draw_overlay') as draw_card, patch.object(home_edit,'draw_reminder_list') as draw_list:
            server.apply_overlays(img, ImageDraw.Draw(img))
        draw_card.assert_called_once()
        self.assertEqual(draw_card.call_args.args[2], fullscreen)
        draw_list.assert_not_called()

    def test_overlay_ids_priority_expiry_and_future_start_filtering(self):
        store=server.overlay_store
        with patch.object(store, '_now', return_value=NOW):
            store.add({'id':'stable-a','slot':'banner','title':'Earlier','text':'first','priority':1,'ttl_seconds':3600})
            store.add({'id':'stable-b','slot':'sidebar','title':'Higher','text':'second','priority':8,'ttl_seconds':3600})
            store.add({'id':'future','slot':'banner','title':'Later','text':'not yet','priority':99,'ttl_seconds':7200,'starts_at':'2026-11-09T08:00:00'})
            store.add({'id':'stable-a','slot':'banner','title':'Updated','text':'replacement','priority':3,'ttl_seconds':3600})
            active=store.active()
            all_records=store.list_all()
        self.assertEqual([o['id'] for o in active],['stable-b','stable-a'])
        self.assertEqual(next(o for o in all_records if o['id']=='stable-a')['text'],'replacement')
        self.assertIn('future',[o['id'] for o in all_records])
        self.assertNotIn('future',[o['id'] for o in active])
        with patch.object(store, '_now', return_value=NOW.replace(hour=20)):
            self.assertEqual(store.active(),[])
            self.assertEqual(store.list_all(),[])

    def test_real_api_render_shows_all_reminders_inside_native_region(self):
        from PIL import ImageChops
        c=server.app.test_client()
        with patch.object(server, 'get_weather', return_value=WEATHER):
            empty=Image.open(io.BytesIO(c.get('/display.bmp').data)).convert('L')
            for i in range(3):
                response=c.post('/overlay',json={'id':f'visible-{i}','slot':'banner' if i%2 else 'sidebar',
                    'title':f'Note {i}','text':'A useful shared reminder', 'priority':i,'ttl_seconds':60})
                self.assertEqual(response.status_code,201)
            actual=Image.open(io.BytesIO(c.get('/display.bmp').data)).convert('L')
        for top in [103,146,189]:
            region=(423,top,766,top+40)
            self.assertIsNotNone(ImageChops.difference(empty.crop(region),actual.crop(region)).getbbox())
        # List drawing must not touch the date or current weather.
        for region in [(0,0,800,58),(0,78,410,343)]:
            self.assertIsNone(ImageChops.difference(empty.crop(region),actual.crop(region)).getbbox())

    def test_long_reminders_are_visibly_ellipsized_within_bounds(self):
        with patch.object(home_edit.ImageDraw.ImageDraw,'text',autospec=True) as text:
            home_edit.render(NOW,WEATHER,reminders=[{'title':'Title '*60,'text':'unbroken'*70}])
        drawn=[call for call in text.call_args_list if call.kwargs.get('font') and call.args[1][0]==423*home_edit.SCALE]
        self.assertTrue(any(call.args[2].endswith('...') for call in drawn))
        for call in drawn:
            if call.args[2]=='REMINDERS':
                continue
            self.assertLessEqual(call.kwargs['font'].getbbox(call.args[2])[2],343*home_edit.SCALE)

    def test_overlay_crud_and_bmp_contract(self):
        c=server.app.test_client()
        r=c.post('/overlay',json={'id':'test-home','slot':'banner','title':'Household','text':'Test only','ttl_seconds':60})
        self.assertEqual(r.status_code,201)
        self.assertEqual(c.get('/overlays?active=1').json['overlays'][0]['id'],'test-home')
        with patch.object(server,'get_weather',return_value=WEATHER):
            response=c.get('/display.bmp?battery=73')
        self.assertEqual(response.status_code,200)
        im=Image.open(io.BytesIO(response.data))
        self.assertEqual(im.mode,'1'); self.assertEqual(im.size,(800,480))
        self.assertLess(len(response.data),50000)
        self.assertEqual(c.delete('/overlay/test-home').status_code,200)
        self.assertEqual(c.get('/overlays?active=1').json['overlays'],[])

    def test_network_failure_is_explicit(self):
        with patch.object(server.requests,'get',side_effect=OSError('offline')):
            self.assertIsNone(server.get_weather(40,-74))
            server._air_cache.clear()
            self.assertIsNone(REAL_GET_AIR_QUALITY(40,-74))
        im=home_edit.render(NOW,None,None)
        self.assertEqual(im.size,(800,480))

if __name__=='__main__': unittest.main()
