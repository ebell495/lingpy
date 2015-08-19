from __future__ import print_function, division, unicode_literals

from mock import patch, Mock

from lingpy import LexStat
from lingpy.util import jsonload
from lingpy.tests.util import test_data, WithTempDir, get_log


class TestLexStat(WithTempDir):
    def setUp(self):
        WithTempDir.setUp(self)
        self.lex = LexStat(test_data('KSL.qlc'))
        self.log = get_log()
        self.get_scorer_kw = dict(runs=10, rands=10, limit=100)

    def test_init(self):
        LexStat({0: ['ID', 'doculect', 'concept', 'IPA']}, model='sca')
        ls = LexStat({0: ['ID', 'doculect', 'concept', 'IPA']})
        self.assertIn('lexstat', repr(ls))
        LexStat(ls)
        LexStat({0: ['ID', 'doculect', 'concept', 'tokens']})
        self.assertRaises(AssertionError, LexStat, {0: ['ID', 'doculect', 'concept']})
        LexStat(test_data('phybo.qlc'), check=True)
        with patch('lingpy.compare.lexstat.log', self.log):
            LexStat(test_data('KSL.qlc'), check=True)
            assert self.log.info.called
        error_log = self.tmp_path('errors')
        with patch('lingpy.util.confirm', Mock(return_value=True)):
            lex = LexStat({
                0: ['ID', 'doculect', 'concept', 'IPA', 'tokens'],
                1: ['1', 'deu', 'hand', 'hand', ['']],
                2: ['2', 'eng', 'hand', 'hand', ['abc']],
                3: ['3', 'xyz', 'hand', 'hund', 'h u n d'],
            }, check=True, errors='%s' % error_log)
            assert error_log.exists()
            self.assertEquals(len(lex._meta['errors']), 2)

    def test_init2(self):
        freqs = self.lex.freqs['Hawaiian']
        for char, n in {'5.W.C': 19, '5.I.V': 87, '5.Y.V': 75, '5.U.V': 87}.items():
            self.assertEquals(freqs[char], n)
        self.assertEquals(len(self.lex.chars), 187)
        self.assertEquals(len(self.lex.rchars), 35)

        self.maxDiff = None

        for name in 'bscorer rscorer pairs'.split():
            obj = jsonload(test_data('KSL.%s.json' % name))
            if name != 'pairs':
                self.assertEquals(getattr(self.lex, name).matrix, obj)
            else:
                for key, values in self.lex.pairs.items():
                    values = set(values)
                    ovalues = set(tuple(v) for v in obj['---'.join(key)])
                    self.assertEquals(values, ovalues)

    def test_getitem(self):
        self.assertIsNone(self.lex['xyz'])

    def test_get_scorer(self):
        self.lex.get_scorer(**self.get_scorer_kw)
        assert hasattr(self.lex, "cscorer")
        with patch('lingpy.compare.lexstat.log', self.log):
            self.lex.get_scorer(**self.get_scorer_kw)
            assert self.log.warn.called
        del self.lex.cscorer
        self.lex.get_scorer(**self.get_scorer_kw)
        self.lex.get_scorer(method='markov', **self.get_scorer_kw)

    def test_cluster(self):
        self.lex.get_scorer(**self.get_scorer_kw)
        self.lex.cluster(method="lexstat", threshold=0.7)
        self.lex.cluster(method="edit-dist", threshold=0.7)
        self.lex.cluster(method="turchin", threshold=0.7)
        self.assertRaises(ValueError, self.lex.cluster, method="fuzzy")
        with patch('lingpy.basic.parser.input', Mock(return_value='y')):
            self.lex.cluster(method="sca", guess_threshold=True, gt_mode='nulld')

        assert 'scaid' in self.lex.header \
            and 'lexstatid' in self.lex.header \
            and 'editid' in self.lex.header \
            and 'turchinid' in self.lex.header

    def test_align_pairs(self):
        self.lex.align_pairs('English', 'German', method='sca')

    def test_get_subset(self):
        self.lex.get_subset([])
        self.assertEquals([v for v in self.lex.subsets.values() if v], [])
        pairs = jsonload(test_data('KSL.pairs.json'))
        self.assertEquals(
            sorted('---'.join(k) for k in self.lex.subsets.keys()),
            sorted(pairs.keys()))

    def test_get_distances(self):
        self.lex.get_scorer(**self.get_scorer_kw)
        self.lex.get_random_distances()
        self.lex.get_distances()
        self.lex.get_distances(method='turchin')
        self.lex.get_distances(aggregate=False)

    def test_get_frequencies(self):
        f = self.lex.get_frequencies('sounds')
        assert len(f) == self.lex.width

        f = self.lex.get_frequencies('sounds', aggregated=True)
        tokens = []
        for k in self.lex:
            for t in self.lex[k, 'tokens']:
                tokens += [t]
        assert len(f) == len(set(tokens))

        d = self.lex.get_frequencies('diversity', ref='cogid')
        assert isinstance(d, float)

        w = self.lex.get_frequencies('wordlength')
        assert len(w) == self.lex.width

        w = self.lex.get_frequencies('wordlength', aggregated=True)
        assert isinstance(w, float)

    def test_output(self):
        self.lex.output('csv', filename='%s' % self.tmp_path('test_lexstat'))
        self.lex.output('scorer', filename='%s' % self.tmp_path('test_lexstat'))

    def test_correctness(self):
        lex = LexStat({
            0: ['ID', 'doculect', 'concept', 'IPA'],
            1: ['1', 'deu', 'hand', 'hand'],
            2: ['2', 'eng', 'hand', 'hand'],
            3: ['3', 'xyz', 'hand', 'xyz']})
        lex.get_scorer(**self.get_scorer_kw)
        lex.cluster(ref='cogid')
        self.assertEquals(lex.get_entries('cogid'), [[1, 1, 3]])

        lex = LexStat({
            0: ['ID', 'concept', 'ipa', 'doculect'],
            1: ['5424', 'Abend::N', 'swar', 'FRA'],
            2: ['5425', 'Abend::N', 'sware', 'FRA'],
            3: ['5426', 'Abend::N', 'sear3', 'RON'],
            4: ['5427', 'Abend::N', 'ivniN', 'ENG'],
            5: ['5428', 'Abend::N', 'noyt3', 'POR'],
            6: ['5429', 'Abend::N', 'tardi5a', 'POR'],
            7: ['5430', 'Abend::N', 'afd3n', 'DAN'],
        })
        lex.get_scorer()
        lex.cluster(method='lexstat', threshold=0.8, ref='cogid')
        self.assertEquals(lex.get_entries('cogid'), [[1, 2, 3, 4, 5], [0, 0, 3, 3, 0]])
