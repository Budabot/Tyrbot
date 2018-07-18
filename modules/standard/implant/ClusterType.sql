DROP TABLE IF EXISTS ClusterType;
CREATE TABLE ClusterType (ClusterTypeID INT NOT NULL PRIMARY KEY, Name VARCHAR(10) NOT NULL);
INSERT INTO ClusterType (ClusterTypeID, Name) VALUES (1,'faded');
INSERT INTO ClusterType (ClusterTypeID, Name) VALUES (2,'bright');
INSERT INTO ClusterType (ClusterTypeID, Name) VALUES (3,'shiny');
