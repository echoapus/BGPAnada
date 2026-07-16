# BGP Message Types (RFC 4271 §4)
MSG_OPEN         = 1
MSG_UPDATE       = 2
MSG_NOTIFICATION = 3
MSG_KEEPALIVE    = 4

# Capability Codes
CAP_MPBGP        = 1   # RFC 4760
CAP_ROUTE_REFRESH= 2
CAP_4BYTE_ASN    = 65  # RFC 6793

# AS_TRANS used in the 2-byte OPEN field when the real ASN is 4 bytes.
AS_TRANS         = 23456

# Address Family Identifiers
AFI_IPV4 = 1
AFI_IPV6 = 2

# Subsequent Address Family Identifiers
SAFI_UNICAST  = 1

# BGP Path Attribute Types
ATTR_ORIGIN          = 1
ATTR_AS_PATH         = 2
ATTR_NEXT_HOP        = 3
ATTR_MED             = 4
ATTR_LOCAL_PREF      = 5
ATTR_ATOMIC_AGGREGATE = 6
ATTR_AGGREGATOR      = 7
ATTR_COMMUNITIES     = 8
ATTR_ORIGINATOR_ID   = 9
ATTR_CLUSTER_LIST    = 10
ATTR_MP_REACH_NLRI   = 14  # RFC 4760
ATTR_MP_UNREACH_NLRI = 15
ATTR_EXT_COMMUNITIES = 16  # RFC 4360
ATTR_AS4_PATH        = 17
ATTR_AS4_AGGREGATOR  = 18
ATTR_IPV6_EXT_COMMUNITIES = 25
ATTR_LARGE_COMMUNITIES = 32

# BGP Header constants
BGP_MARKER     = b'\xff' * 16
BGP_HEADER_LEN = 19   # marker(16) + length(2) + type(1)
