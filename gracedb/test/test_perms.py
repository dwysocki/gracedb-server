from django.test import TestCase

class SimpleTest(TestCase): 
    # I wonder if the order of loading the fixtures will matter?
    fixtures = [
        'perm_test/auth_permission.json',
        'perm_test/auth_user.json',
        'perm_test/gracedb_group.json',
        'perm_test/gracedb_label.json',
        'perm_test/gracedb_event.json',
        'perm_test/gracedb_grbevent.json',
        'perm_test/gracedb_multiburstevent.json',
        'perm_test/gracedb_coincinspiralevent.json',
        'perm_test/gracedb_singleinspiral.json',
        'perm_test/gracedb_eventlog.json',
        'perm_test/gracedb_tag.json',
    ] 

    def test_index(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_search(self):
        response = self.client.get('/events/search/')
        self.assertEqual(response.status_code, 200)

    def test_event_view(self):
        url = '/events/view/T121326'
        response = self.client.get(url,REMOTE_USER='gra')
        #print "Response content: "
        #print response.content
        self.assertEqual(response.status_code, 200)
        self.client.logout()
