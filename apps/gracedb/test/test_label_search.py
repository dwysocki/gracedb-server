from django.test import TestCase
from django.db.models import Q
from django.contrib.auth.models import User
from gracedb.models import Event, Label, Labelling
from gracedb.models import Group, Pipeline
from gracedb.query import parseQuery, filter_for_labels

QUERY_CASES = {
    'all_ors'             : { 'query': 'A_LABEL | B_LABEL | C_LABEL',    'pk_list': [2,3,4,5,6,7,8] },
    'all_ands'            : { 'query': 'A_LABEL & B_LABEL & C_LABEL',    'pk_list': [8] },
    'not_a'               : { 'query': '~A_LABEL',                       'pk_list': [1,3,4,7] },
    'a_and_b'             : { 'query': 'A_LABEL & B_LABEL',              'pk_list': [5,8] },
    'a_or_b'              : { 'query': 'A_LABEL | B_LABEL',              'pk_list': [ 2,3,5,6,7,8] },
    'a_or_not_b'          : { 'query': 'A_LABEL | ~B_LABEL',             'pk_list': [1,2,4,5,6,8] },
    'a_and_not_b'         : { 'query': 'A_LABEL & ~B_LABEL',             'pk_list': [2,6] },
    'one_or_more_missing' : { 'query': '~A_LABEL | ~B_LABEL | ~C_LABEL', 'pk_list': [1,2,3,4,5,6,7] },
}

def get_pks_for_query(queryString):
    qs = Event.objects.filter(parseQuery(queryString))
    qs = filter_for_labels(qs, queryString)
    qs = qs.distinct()
    return [int(obj.id) for obj in qs]

class LabelSearchTestCase(TestCase):
    def setUp(self):

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

        for label_list in label_lists:
            e = Event.objects.create(submitter=submitter, group=group, pipeline=pipeline)
            for label in label_list:
                Labelling.objects.create(event=e, label=label, creator=submitter)

    def test_all_queries(self):
        for key, d in QUERY_CASES.iteritems():
            print "Checking %s ... " % key
            # Explicitly search for test events
            query = 'Test ' + d['query']
            self.assertEqual(set(get_pks_for_query(query)), set(d['pk_list']))

    def test_bad_query(self):
        f = Q(labels__name='A_LABEL') | ~Q(labels__name='B_LABEL')
        qs = Event.objects.filter(f)
        results = [int(obj.id) for obj in qs]
        self.assertEqual(set(results), set([1,2,4,5,6,7,8]))

    def test_other_query(self):
        f1 = Q(labels__name='A_LABEL') 
        f2 = ~Q(labels__name='B_LABEL')
        qs = Event.objects.filter(f1) | Event.objects.filter(f2)
        results = [int(obj.id) for obj in qs]
        self.assertEqual(set(results), set([1,2,4,5,6,8]))

    def test_intersect_query(self):
        f1 = Q(labels__name='A_LABEL') 
        f2 = ~Q(labels__name='B_LABEL')
        qs = Event.objects.filter(f1) & Event.objects.filter(f2)
        results = [int(obj.id) for obj in qs]
        self.assertEqual(set(results), set([2,6]))

    def test_qs_order_op(self):
        # This does (A and B) or C
        f1 = Q(labels__name='A_LABEL') 
        f2 = Q(labels__name='B_LABEL')
        f3 = Q(labels__name='C_LABEL')
        qs = Event.objects.filter(f1) & Event.objects.filter(f2) | Event.objects.filter(f3)
        results = [int(obj.id) for obj in qs]
        self.assertEqual(set(results), set([4,5,6,7,8]))

    def test_qs_order_op2(self):
        # This does A and (B or C)
        f1 = Q(labels__name='A_LABEL') 
        f2 = Q(labels__name='B_LABEL')
        f3 = Q(labels__name='C_LABEL')
        qs = Event.objects.filter(f2) | Event.objects.filter(f3)
        qs = Event.objects.filter(f1) & qs
        results = [int(obj.id) for obj in qs]
        self.assertEqual(set(results), set([5,6,8]))

