import pytest
from django.test import TestCase
from django.db.models import Q
from django.contrib.auth.models import User
from events.models import Event, Label, Labelling
from events.models import Group, Pipeline
from search.query.events import parseQuery
from search.query.labels import filter_for_labels


def get_pks_for_query(queryString):
    qs = Event.objects.filter(parseQuery(queryString))
    qs = filter_for_labels(qs, queryString)
    return [int(obj.id) for obj in qs]

class LabelSearchTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):

        # Start by clearing out some objects. This is being a littl conservative,
        # but I don't know what's bleeding in from earlier tests.

        for obj in Label.objects.all():
            obj.delete()

        for obj in Labelling.objects.all():
            obj.delete()

        for obj in Event.objects.all():
            obj.delete()

        a = Label.objects.create(name='A_LABEL')
        b = Label.objects.create(name='B_LABEL')
        c = Label.objects.create(name='C_LABEL')

        # Primary keys start with 1. 1 to 8 here.
        label_lists = [
            [],
            [a],
            [b],
            [c],
            [a, b],
            [a, c],
            [b, c],
            [a, b, c],
        ]

        # The required fields on event are: submitter, group, pipeline
        submitter = User.objects.create(username='albert.einstein@LIGO.ORG')
        group     = Group.objects.create(name='Test')
        pipeline  = Pipeline.objects.create(name='TestPipeline')

        pkl = [[] for i in label_lists]

        for i, label_list in enumerate(label_lists):
            e = Event.objects.create(submitter=submitter, group=group, pipeline=pipeline)
            pkl[i]=e.pk
            for label in label_list:
                Labelling.objects.create(event=e, label=label, creator=submitter)
        cls.pkl = pkl

        cls.QUERY_CASES = {
            'all_ors'             : { 'query': 'A_LABEL | B_LABEL | C_LABEL',    'pk_list': [pkl[1],pkl[2],pkl[3],pkl[4],pkl[5],pkl[6],pkl[7]] },
            'all_ands'            : { 'query': 'A_LABEL & B_LABEL & C_LABEL',    'pk_list': [pkl[7]] },
            'not_a'               : { 'query': '~A_LABEL',                       'pk_list': [pkl[0],pkl[2],pkl[3],pkl[6]] },
            'a_and_b'             : { 'query': 'A_LABEL & B_LABEL',              'pk_list': [pkl[4],pkl[7]] },
            'a_or_b'              : { 'query': 'A_LABEL | B_LABEL',              'pk_list': [pkl[1],pkl[2],pkl[4],pkl[5],pkl[6],pkl[7]] },
            'a_or_not_b'          : { 'query': 'A_LABEL | ~B_LABEL',             'pk_list': [pkl[0],pkl[1],pkl[3],pkl[4],pkl[5],pkl[7]] },
            'a_and_not_b'         : { 'query': 'A_LABEL & ~B_LABEL',             'pk_list': [pkl[1],pkl[5]] },
            'one_or_more_missing' : { 'query': '~A_LABEL | ~B_LABEL | ~C_LABEL', 'pk_list': [pkl[0],pkl[1],pkl[2],pkl[3],pkl[4],pkl[5],pkl[6]] },
        }
        super(LabelSearchTestCase,cls).setUpTestData()

    def tearDown(cls):
        # Delete stuff:
        for obj in Label.objects.all():
            obj.delete()

        for obj in Labelling.objects.all():
            obj.delete()

        for obj in Event.objects.all():
            obj.delete()

        super(LabelSearchTestCase,cls).tearDown()

    @pytest.mark.django_db(transaction=True, reset_sequences=True)
    def test_all_queries(self):
        i = 0
        for key, d in self.QUERY_CASES.items():
            print("Checking %s ... " % key)
            # Explicitly search for test events
            query = 'Test ' + d['query']
            self.assertEqual(set(get_pks_for_query(query)), set(d['pk_list']))
            i += 1

    @pytest.mark.django_db(transaction=True, reset_sequences=True)
    def test_bad_query(self):
        pkl = self.pkl
        f = Q(labels__name='A_LABEL') | ~Q(labels__name='B_LABEL')
        qs = Event.objects.filter(f)
        results = [int(obj.id) for obj in qs]
        self.assertEqual(set(results), set([pkl[0],pkl[1],pkl[3],pkl[4],pkl[5],pkl[6],pkl[7]]))

    @pytest.mark.django_db(transaction=True, reset_sequences=True)
    def test_other_query(self):
        pkl = self.pkl
        f1 = Q(labels__name='A_LABEL') 
        f2 = ~Q(labels__name='B_LABEL')
        qs = Event.objects.filter(f1) | Event.objects.filter(f2)
        results = [int(obj.id) for obj in qs]
        self.assertEqual(set(results), set([pkl[0],pkl[1],pkl[3],pkl[4],pkl[5],pkl[7]]))

    @pytest.mark.django_db(transaction=True, reset_sequences=True)
    def test_intersect_query(self):
        pkl = self.pkl
        f1 = Q(labels__name='A_LABEL') 
        f2 = ~Q(labels__name='B_LABEL')
        qs = Event.objects.filter(f1) & Event.objects.filter(f2)
        results = [int(obj.id) for obj in qs]
        self.assertEqual(set(results), set([pkl[1],pkl[5]]))

    @pytest.mark.django_db(transaction=True, reset_sequences=True)
    def test_qs_order_op(self):
        pkl = self.pkl
        # This does (A and B) or C
        f1 = Q(labels__name='A_LABEL') 
        f2 = Q(labels__name='B_LABEL')
        f3 = Q(labels__name='C_LABEL')
        qs = Event.objects.filter(f1) & Event.objects.filter(f2) | Event.objects.filter(f3)
        results = [int(obj.id) for obj in qs]
        self.assertEqual(set(results), set([pkl[3],pkl[4],pkl[5],pkl[6],pkl[7]]))

    @pytest.mark.django_db(transaction=True, reset_sequences=True)
    def test_qs_order_op2(self):
        pkl = self.pkl
        # This does A and (B or C)
        f1 = Q(labels__name='A_LABEL') 
        f2 = Q(labels__name='B_LABEL')
        f3 = Q(labels__name='C_LABEL')
        qs = Event.objects.filter(f2) | Event.objects.filter(f3)
        qs = Event.objects.filter(f1) & qs
        results = [int(obj.id) for obj in qs]
        self.assertEqual(set(results), set([pkl[4],pkl[5],pkl[7]]))

