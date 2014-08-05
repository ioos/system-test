from pyoos.collectors.nerrs.nerrs_soap import NerrsSoap
from datetime import datetime, timedelta

def main():

  nerrsData = NerrsSoap()
  nerrsData.filter(features=['ACEBPMET', 'SFBFMWQ'],
                    start=datetime.utcnow() - timedelta(hours=24),
                   end=datetime.utcnow()  - timedelta(hours=12))

  #nerrsData.filter(variables=["ATemp"])
  raw = nerrsData.raw()
  response = nerrsData.collect()
  for obsRec in response:
    #stationRec = obsRec.feature
    for stationRec in response.get_elements():
      print "Station: %s Location: %s" % (stationRec.name, stationRec.get_location())

      #The elements are a list of the observed_properties returned wrapped in a Point object.
      for obsProp in stationRec.get_elements():
        print "Observation Date/Time: %s" % (obsProp.get_time())
        #print "Member names: %s" % (obsProp.get_member_names())
        #I think that for a multi sensor request, there should be multiple members, each representing
        #a specific observed_property.
        for member in obsProp.get_members():
          #Apparently you're going to have to know how each collector parses the pieces of the data.
          #For an SOS query, there appear to be: name, units, value, and standard(CF MMI link).
          for key,value in member.iteritems():
            print "%s = %s" % (key, value)


  return


if __name__ == "__main__":
  main()