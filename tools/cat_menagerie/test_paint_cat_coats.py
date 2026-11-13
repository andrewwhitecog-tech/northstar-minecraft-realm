"""Real tests for future hosted export; authored here, NOT executed locally."""
import binascii
import json
import math
from pathlib import Path
import struct
import tempfile
import unittest
import zlib
import paint_cat_coats as P


def decode_original_png(blob):
    if blob[:8]!=b'\x89PNG\r\n\x1a\n': raise ValueError('signature')
    pos=8; compressed=b''; size=None; ended=False
    while pos<len(blob):
        n=struct.unpack('>I',blob[pos:pos+4])[0]; kind=blob[pos+4:pos+8]; data=blob[pos+8:pos+8+n]
        crc=struct.unpack('>I',blob[pos+8+n:pos+12+n])[0]
        if zlib.crc32(kind+data)&0xffffffff!=crc: raise ValueError('CRC')
        if kind==b'IHDR':
            w,h,depth,mode,comp,filt,interlace=struct.unpack('>IIBBBBB',data)
            if (depth,mode,comp,filt,interlace)!=(8,6,0,0,0): raise ValueError('RGBA8 required')
            size=(w,h)
        elif kind==b'IDAT': compressed+=data
        elif kind==b'IEND': ended=True
        pos+=12+n
    if not ended or pos!=len(blob) or size is None: raise ValueError('truncated PNG')
    w,h=size; raw=zlib.decompress(compressed)
    if len(raw)!=(w*4+1)*h: raise ValueError('pixel length')
    if any(raw[y*(w*4+1)]!=0 for y in range(h)): raise ValueError('unexpected filter')
    return w,h,b''.join(raw[y*(w*4+1)+1:(y+1)*(w*4+1)] for y in range(h))

class GeometryAndPaintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.roster,cls.recipes,cls.models,cls.bedrock=P.validate_inputs()

    def test_exact_roster_coverage_reuse_is_reference_only(self):
        self.assertEqual(len(self.roster),65)
        self.assertEqual({r['id'] for r in self.roster if r['reuseVanilla']},
                         {'minecraft:british_shorthair','minecraft:persian','minecraft:ragdoll','minecraft:siamese'})
        self.assertEqual(set(self.recipes),{r['id'] for r in self.roster if not r['reuseVanilla']})
        self.assertTrue(all(k.startswith('nsp_cat_coats:') for k in self.recipes))

    def test_official_baby_is_independent_mesh_not_adult_resize(self):
        adult={c['name']:c for c in self.models['adult']['cubes']}; baby={c['name']:c for c in self.models['baby']['cubes']}
        self.assertEqual(adult['body']['uv'],[20,0]); self.assertEqual(adult['body']['size'],[4,16,6])
        self.assertEqual(baby['body']['uv'],[0,8]); self.assertEqual(baby['body']['size'],[4,3,7])
        self.assertEqual(baby['nose']['uv'],[18,3]); self.assertEqual(baby['tail1']['uv'],[0,18])
        self.assertNotIn('tail2',baby)
        self.assertEqual(P.face_rects([0,0],[5,4,5])['north'],(5,5,5,4))
        self.assertEqual(P.face_rects([0,0],[5,4,4])['north'],(4,4,5,4))

    def test_native_uv_eye_landmarks_at_independent_coordinates(self):
        r=self.recipes['nsp_cat_coats:domestic_balinese']; iris=bytes((*P.color(r['iris']),255))
        for name,eye,width in [('adult',(6,6),64),('baby',(5,5),32)]:
            pixels,_=P.paint_model(self.models[name],r); i=(eye[1]*width+eye[0])*4
            self.assertEqual(pixels[i:i+4],iris,name)
            self.assertEqual(len(pixels),width*32*4)

    def test_all_authored_geometry_uv_and_bone_regions_are_bounded(self):
        self.assertEqual(len(self.bedrock),19)
        for name,m in self.bedrock.items():
            for c in m['cubes']:
                with self.subTest(profile=name,cube=c['name']): P.validate_cube(c,128,64)
        self.assertIn('mane',{c['region'] for c in self.bedrock['mane']['cubes']})
        self.assertIn('ribbon',{c['region'] for c in self.bedrock['pastry_harness_rainbow_tail']['cubes']})
        self.assertIn('crystal',{c['region'] for c in self.bedrock['crystal_trim']['cubes']})

    def test_reject_outside_atlas_before_paint(self):
        bad={'name':'bad','uv':[127,63],'size':[2,2,2]}
        with self.assertRaisesRegex(ValueError,'outside atlas'): P.validate_cube(bad,128,64)
        for size in ([0,1,1],[-1,2,3],[True,1,1],[math.nan,1,1]):
            with self.subTest(size=size),self.assertRaises(ValueError): P.validate_cube({**bad,'size':size},128,64)

    def test_jaguar_has_center_dot_leopard_open_rosette_center(self):
        base=dict(self.recipes['nsp_cat_coats:mini_leopard'],density=4,phase=.35,mark='none')
        jag={**base,'pattern':'central_rosettes'}
        t=(2-.35)/4
        self.assertNotEqual(P.marking(base,.5,0,t,'body'),'dark')
        self.assertEqual(P.marking(jag,.5,0,t,'body'),'dark')
        ring=(2.34-.35)/4
        self.assertEqual(P.marking(base,.5,0,ring,'body'),'dark')
        self.assertEqual(P.marking(jag,.5,0,ring,'body'),'dark')

    def test_tiger_and_cheetah_masks_are_not_recolors(self):
        a=self.recipes['nsp_cat_coats:mini_tiger']; b=self.recipes['nsp_cat_coats:mini_cheetah']
        def mask(r): return [P.marking(r,.3,h/20,t/40,'body')=='dark' for h in range(21) for t in range(41)]
        ma,mb=mask(a),mask(b)
        self.assertNotEqual(ma,mb); self.assertGreater(sum(ma),sum(mb)); self.assertGreater(sum(mb),0)
        self.assertEqual(b['mark'],'tears')

    def test_birman_white_gloves_override_dark_points(self):
        r=self.recipes['nsp_cat_coats:domestic_birman']
        self.assertEqual(P.marking(r,.5,.1,.5,'leg'),'light')
        self.assertEqual(P.marking(r,.5,.6,.5,'tail'),'dark')

    def test_fantasy_patterns_distinct_and_crystals_not_fur(self):
        ids=[k for k in self.recipes if k.startswith('nsp_cat_coats:fantasy_')]
        self.assertEqual(len(ids),5); masks=[]
        for k in ids:
            r=self.recipes[k]; mask=tuple(P.marking(r,.3,h/20,t/30,'body') for h in range(21) for t in range(31)); masks.append(mask)
            self.assertIn('gold' if r['pattern'] in ('portal','guilloche','loomwheel') else ('opal' if r['pattern']=='opal' else 'rainbow'),mask)
            self.assertEqual(P.marking(r,.5,.5,.5,'crystal'),'crystal')
        self.assertEqual(len(set(masks)),5)

    def test_nyan_actual_pastry_and_six_band_geometry_masks(self):
        r=self.recipes['nsp_cat_coats:rare_nyan']
        tags={P.marking(r,.5,h/20,t/30,'pastry') for h in range(21) for t in range(31)}
        self.assertTrue({'crust','icing','sprinkle'}<=tags)
        self.assertEqual(P.marking(r,.5,.5,.5,'ribbon'),'rainbow_band')
        m=self.bedrock['pastry_harness_rainbow_tail']
        c=next(c for c in m['cubes'] if c['region']=='ribbon')
        colors={P.sample(r,c,'north',.5,v,'bedrock_up')[:3] for v in [1/12,3/12,5/12,7/12,9/12,11/12]}
        self.assertEqual(len(colors),6)

    def test_png_crc_roundtrip_and_corruption_rejection(self):
        original=bytes(range(16)); b=P.png_bytes(2,2,original)
        self.assertEqual(decode_original_png(b),(2,2,original))
        broken=bytearray(b); broken[20]^=1
        with self.assertRaisesRegex(ValueError,'CRC'): decode_original_png(bytes(broken))
        with self.assertRaises(ValueError): P.png_bytes(2,2,b'bad')

    def test_official_top_uv_corner_is_back_edge_not_front_edge(self):
        # Official ModelPart.Cube DOWN polygon on minY uses vertices24,23,19,20.
        # Polygon remap puts UV00 at vertex23 = minX,minY,maxZ.
        self.assertEqual(P.surface('up',0,0),(0,1,1))
        self.assertEqual(P.surface('up',1,1),(1,1,0))
        self.assertEqual(P.surface('north',0,0),(0,1,0))

    def test_coat_ruff_is_fur_and_only_actual_muzzle_is_nose(self):
        for profile in ('long_coat','long_tail_fluff','curled_coat'):
            cubes=self.bedrock[profile]['cubes']
            ruff=[c for c in cubes if c['name']=='head_3']
            self.assertEqual(len(ruff),1,profile)
            self.assertEqual(ruff[0]['region'],'ruff',profile)
            self.assertFalse(any(c['region']=='nose' for c in cubes),profile)
        self.assertEqual([c['region'] for c in self.bedrock['broad_muzzle']['cubes'] if c['name']=='head_3'],['nose'])

    def test_fantasy_keeps_dark_anatomy_and_localized_continuous_aurora(self):
        for name,r in self.recipes.items():
            if not name.startswith('nsp_cat_coats:fantasy_'): continue
            with self.subTest(coat=name):
                tags=[P.marking(r,.35,h/50,t/80,'body') for h in range(51) for t in range(81)]
                self.assertGreater(tags.count('base')/len(tags),.55)
                self.assertEqual(P.marking(r,.35,.05,.05,'body'),'base')
                # A real nonparallel stream follows the authored body curve.
                for t in (.2,.4,.5,.8):
                    h=.57+.16*math.sin(t*5.4+r['phase']*5)
                    self.assertIn(P.marking(r,.35,h,t,'body'),('rainbow','gold','opal'))

class ExportTests(unittest.TestCase):
    def test_explicit_nyan_art_gate_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'gated'
            with self.assertRaisesRegex(ValueError,'include-nyan-original'): P.export(p,False)
            self.assertFalse(p.exists())

    def test_export_all61_sets_is_original_deterministic_and_no_install(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'original-paint'; receipt=P.export(out,True)
            pngs=list(out.rglob('*.png')); self.assertEqual(len(pngs),183)
            self.assertEqual({p.name for p in pngs},{'adult.png','baby.png','bedrock.png'})
            for p in pngs:
                with self.subTest(path=p.relative_to(out)):
                    w,h,pixels=decode_original_png(p.read_bytes())
                    self.assertEqual((w,h),{'adult.png':(64,32),'baby.png':(32,32),'bedrock.png':(128,64)}[p.name])
                    self.assertGreater(sum(pixels[3::4]),0)
                    self.assertGreater(len(set(zip(pixels[0::4],pixels[1::4],pixels[2::4]))),8)
            r=P.read_json(P.HERE/'coat_recipes.json')['recipes']['nsp_cat_coats:mini_tiger']
            m=P.read_json(P.HERE/'uv_models.json')['baby']; data,_=P.paint_model(m,r)
            self.assertEqual((out/'originals/mini_tiger/baby.png').read_bytes(),P.png_bytes(32,32,data))
            self.assertFalse(receipt['nativeRun']); self.assertFalse(receipt['gameInstalled']); self.assertFalse(receipt['mappingIDsAssigned'])
            self.assertFalse(any((out/n).exists() for n in ('manifest.json','world','mods','mappings')))
            html=(out/'RENDER_REVIEW.html').read_text(); self.assertNotIn('/*MODEL_DATA*/',html)
            self.assertIn("getContext('webgl'",html); self.assertNotIn('<iframe',html)
            self.assertNotIn('minecraft_british_shorthair',{p.parent.name for p in pngs})

    def test_existing_output_preserved_and_live_paths_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'kept'; out.mkdir(); marker=out/'existing.txt'; marker.write_text('preserve')
            with self.assertRaises(FileExistsError): P.export(out,True)
            self.assertEqual(marker.read_text(),'preserve')
            with self.assertRaisesRegex(ValueError,'live/profile/world'): P.export(Path(d)/'saves'/'new',True)
            self.assertFalse((Path(d)/'saves').exists())

if __name__=='__main__': unittest.main(verbosity=2)
