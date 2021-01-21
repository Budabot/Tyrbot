from core.chat_blob import ChatBlob
from core.decorators import instance, command
from core.db import DB
from core.command_param_types import Any


@instance()
class ClusterController:
    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.text = registry.get_instance("text")
        self.command_alias_service = registry.get_instance("command_alias_service")

    def start(self):
        self.command_alias_service.add_alias("clusters", "cluster")

    @command(command="cluster", params=[], access_level="all",
             description="Show a list of implant slots and a list of attributes that can be buffed with an implant cluster")
    def cluster_list_cmd(self, request):
        data = self.db.query("SELECT Name, ShortName FROM ImplantType ORDER BY ImplantTypeID ASC")
        blob = "<header2>Slots (%d)</header2>\n" % len(data)
        for row in data:
            blob += self.text.make_chatcmd(row.Name, "/tell <myname> cluster %s" % row.ShortName) + "\n"

        data = self.db.query("SELECT ClusterID, LongName FROM Cluster WHERE ClusterID != 0 ORDER BY LongName ASC")
        blob += "\n<header2>Attributes (%d)</header2>\n" % len(data)
        for row in data:
            blob += self.text.make_chatcmd(row["LongName"], "/tell <myname> cluster %s" % row["LongName"]) + "\n"

        return ChatBlob("Clusters", blob)

    @command(command="cluster", params=[Any("attribute_or_slot")], access_level="all",
             description="Show which clusters buff a particular attribute, or which attributes can be buffed from a particular slot")
    def cluster_attribute_cmd(self, request, search):
        slot_data = self.db.query("SELECT ImplantTypeID, Name, ShortName FROM ImplantType WHERE Name <EXTENDED_LIKE=0> ? OR ShortName <EXTENDED_LIKE=1> ?",
                                  [search, search], extended_like=True)
        slot_count = len(slot_data)

        if slot_count == 1:
            implant_type = slot_data[0]
            data = self.db.query("SELECT c2.Name AS cluster_type, c3.LongName AS attribute FROM ClusterImplantMap c1 "
                                 "JOIN ClusterType c2 ON c1.ClusterTypeID = c2.ClusterTypeID JOIN Cluster c3 ON c1.ClusterID = c3.ClusterID "
                                 "WHERE ImplantTypeID = ? "
                                 "ORDER BY c2.ClusterTypeID DESC, c3.LongName ASC", [implant_type.ImplantTypeID])
            return self.format_slot_output(implant_type.Name, data)
        else:
            attribute_data = self.db.query("SELECT ClusterID, LongName FROM Cluster WHERE LongName <EXTENDED_LIKE=0> ?", [search], extended_like=True)
            attribute_count = len(attribute_data)

            if attribute_count == 0:
                return "No attributes or slots found that match <highlight>%s</highlight>." % search
            else:
                return self.format_attribute_output(attribute_data)

    def format_attribute_output(self, data):
        count = len(data)
        blob = ""
        for row in data:
            data2 = self.db.query("SELECT i.ShortName as Slot, c2.Name AS ClusterType "
                                  "FROM ClusterImplantMap c1 "
                                  "JOIN ClusterType c2 ON c1.ClusterTypeID = c2.ClusterTypeID "
                                  "JOIN ImplantType i ON c1.ImplantTypeID = i.ImplantTypeID "
                                  "WHERE c1.ClusterID = ? "
                                  "ORDER BY c2.ClusterTypeID DESC", [row["ClusterID"]])

            blob += "<pagebreak><header2>%s</header2>\n" % row["LongName"]
            for row2 in data2:
                blob += "%s: <highlight>%s</highlight><tab>" % (row2["ClusterType"].capitalize(), row2["Slot"])
            blob += "\n\n"
        blob += "\n* indicates Jobe Cluster"

        return ChatBlob("Cluster Search Results (%d)" % count, blob)

    def format_slot_output(self, slot, data):
        count = len(data)
        blob = ""
        current_cluster_type = ""
        for row in data:
            if row.cluster_type != current_cluster_type:
                blob += "\n<header2>%s</header2>\n" % row.cluster_type.capitalize()
                current_cluster_type = row.cluster_type
            blob += self.text.make_chatcmd(row.attribute, "/tell <myname> cluster %s" % row.attribute) + "\n"
        blob += "\n\n"
        blob += "* indicates Jobe Cluster"

        return ChatBlob("%s Attributes (%d)" % (slot, count), blob)
