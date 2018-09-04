from core.chat_blob import ChatBlob
from core.decorators import instance, command
from core.db import DB
from core.command_param_types import Any


@instance()
class ClusterController:
    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.text = registry.get_instance("text")

    @command(command="cluster", params=[], access_level="all",
             description="Show a list of skills that can be buffed with an implant cluster")
    def cluster_list_cmd(self, request):
        data = self.db.query("SELECT ClusterID, LongName FROM Cluster ORDER BY LongName ASC")

        blob = ""
        for row in data:
            blob += self.text.make_chatcmd(row["LongName"], "/tell <myname> cluster %s" % row["LongName"]) + "\n"

        return ChatBlob("Cluster List (%d)" % len(data), blob)

    @command(command="cluster", params=[Any("skill")], access_level="all",
             description="Show which clusters buff a particular skill")
    def cluster_show_cmd(self, request, skill):
        data = self.db.query("SELECT ClusterID, LongName FROM Cluster WHERE LongNAme <EXTENDED_LIKE=0> ?", [skill], extended_like=True)
        count = len(data)

        if count == 0:
            return "No skills found that match <highlight>%s<end>." % skill
        else:
            blob = ""
            for row in data:
                data2 = self.db.query("SELECT i.ShortName as Slot, c2.Name AS ClusterType "
                                      "FROM ClusterImplantMap c1 "
                                      "JOIN ClusterType c2 ON c1.ClusterTypeID = c2.ClusterTypeID "
                                      "JOIN ImplantType i ON c1.ImplantTypeID = i.ImplantTypeID "
                                      "WHERE c1.ClusterID = ? "
                                      "ORDER BY c2.ClusterTypeID DESC", [row["ClusterID"]])

                blob += "<pagebreak><header2>%s<end>\n" % row["LongName"]
                for row2 in data2:
                    blob += "%s: <highlight>%s<end><tab>" % (row2["ClusterType"].capitalize(), row2["Slot"])
                blob += "\n\n"

            return ChatBlob("Cluster Search Results (%d)" % count, blob)
