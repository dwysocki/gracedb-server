.. _new_event_subclass:

==================================
Creating a new event subclass
==================================

Why?
==========
Most events in GraceDB have attributes that go beyond those in the base
event class. If a new pipeline is developed, and the data analysts wish
to upload events to GraceDB, these events will often have attributes
that do not correspond to any of the existing event subclasses. In this
case, you will need to create a new event subclass. 
