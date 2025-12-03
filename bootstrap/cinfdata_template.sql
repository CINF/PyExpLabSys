/*M!999999\- enable the sandbox mode */ 
-- MariaDB dump 10.19  Distrib 10.6.22-MariaDB, for debian-linux-gnu (x86_64)
--
-- Host: localhost    Database: nanomadedata
-- ------------------------------------------------------
-- Server version	10.6.22-MariaDB-0ubuntu0.22.04.1

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `alarm`
--

DROP TABLE IF EXISTS `alarm`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `alarm` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `quiries_json` varchar(16384) NOT NULL,
  `parameters_json` varchar(256) NOT NULL,
  `check` varchar(128) NOT NULL,
  `no_repeat_interval` int(10) NOT NULL,
  `message` varchar(8192) NOT NULL,
  `recipients_json` varchar(512) NOT NULL,
  `locked` tinyint(1) NOT NULL,
  `visible` tinyint(1) NOT NULL,
  `description` varchar(128) NOT NULL,
  `subject` varchar(128) NOT NULL,
  `active` int(4) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM AUTO_INCREMENT=24 DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `alarm_log`
--

DROP TABLE IF EXISTS `alarm_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `alarm_log` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `alarm_id` int(10) unsigned NOT NULL,
  `time` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`)
) ENGINE=MyISAM AUTO_INCREMENT=1325 DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `dateplots_cryostat`
--
DROP TABLE IF EXISTS `dateplots_cryostat`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `dateplots_cryostat` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `time` timestamp NOT NULL DEFAULT current_timestamp(),
  `type` smallint(5) unsigned NOT NULL,
  `value` double DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `time` (`time`)
) ENGINE=MyISAM AUTO_INCREMENT=2624718 DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `dateplots_descriptions`
--
DROP TABLE IF EXISTS `dateplots_descriptions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `dateplots_descriptions` (
  `id` smallint(5) unsigned NOT NULL,
  `codename` char(255) NOT NULL,
  `description` char(255) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;


--
-- Table structure for table `measurements_cryostat`
--
DROP TABLE IF EXISTS `measurements_cryostat`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `measurements_cryostat` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `time` timestamp NOT NULL DEFAULT current_timestamp(),
  `type` int(10) unsigned NOT NULL COMMENT 'Type of measurement, as found in the types table',
  `timestep` double DEFAULT NULL COMMENT 'Time pr. step for the xy-values',
  `comment` varchar(255) NOT NULL COMMENT 'Comment',
  `label` varchar(45) DEFAULT NULL,
  `mass` varchar(45) DEFAULT NULL,
  `frequency` float DEFAULT NULL,
  `current` float DEFAULT NULL,
  `delta_i` float DEFAULT NULL,
  `nplc` float DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM AUTO_INCREMENT=7301 DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `measurements_dummy`
--
DROP TABLE IF EXISTS `measurements_dummy`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `measurements_dummy` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `time` timestamp NOT NULL DEFAULT current_timestamp(),
  `type` int(10) unsigned NOT NULL COMMENT 'Type of measurement, as found in the types table',
  `timestep` double DEFAULT NULL COMMENT 'Time pr. step for the xy-values',
  `comment` varchar(45) NOT NULL COMMENT 'Comment',
  `label` varchar(45) NOT NULL,
  `preamp_range` smallint(6) DEFAULT NULL,
  `frequency` float DEFAULT NULL,
  `current` float DEFAULT NULL,
  `delta_i` float DEFAULT NULL,
  `nplc` float DEFAULT NULL,
  `timeconstant` float DEFAULT NULL,
  `sensitivity` float DEFAULT NULL,
  `slope` varchar(45) DEFAULT NULL,
  `reserve` varchar(45) DEFAULT NULL,
  `coupling` varchar(45) DEFAULT NULL,
  `voltage` float DEFAULT NULL,
  `klaf` float DEFAULT NULL,
  `limit` float DEFAULT NULL,
  `steps` int(11) DEFAULT NULL,
  `repeats` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM AUTO_INCREMENT=10357 DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;


--
-- Table structure for table `plot_com`
--
DROP TABLE IF EXISTS `plot_com`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `plot_com` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `input` blob DEFAULT NULL,
  `output` blob DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `plot_com_in`
--
DROP TABLE IF EXISTS `plot_com_in`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `plot_com_in` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `input` blob DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM AUTO_INCREMENT=39535 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `plot_com_out`
--
DROP TABLE IF EXISTS `plot_com_out`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `plot_com_out` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `output` blob DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM AUTO_INCREMENT=1168 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `short_links`
--
DROP TABLE IF EXISTS `short_links`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `short_links` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `url` varchar(1024) NOT NULL,
  `comment` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM AUTO_INCREMENT=14 DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `xy_values_cryostat`
--
DROP TABLE IF EXISTS `xy_values_cryostat`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `xy_values_cryostat` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `measurement` int(10) unsigned NOT NULL,
  `x` double NOT NULL,
  `y` double NOT NULL,
  PRIMARY KEY (`id`),
  KEY `measurement` (`measurement`)
) ENGINE=MyISAM AUTO_INCREMENT=103686640 DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `xy_values_dummy`
--

DROP TABLE IF EXISTS `xy_values_dummy`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `xy_values_dummy` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `measurement` int(10) unsigned NOT NULL,
  `x` double NOT NULL,
  `y` double NOT NULL,
  PRIMARY KEY (`id`),
  KEY `measurement` (`measurement`)
) ENGINE=MyISAM AUTO_INCREMENT=2842935 DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-11-04 11:54:38
