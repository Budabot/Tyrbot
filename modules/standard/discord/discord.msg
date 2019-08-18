{
  "blob": {
    "en_US": [
      "<header2>Info<end>\n",
      "Status: {connected}\n",
      "Channels available: <highlight>{count}<end>\n\n",
      "<header2>Servers<end>\n",
      "{servers}\n",
      "<header2>Subscribed channels<end>\n",
      "{subs}",
      "\n\nDiscord Module written by <highlight>Vladimirovna<end>\n"
    ],
    "de_DE": [
      "<header2>Informationen<end>\n",
      "Status: {connected}\n",
      "Verfügbare Channel: <highlight>{count}<end>\n\n",
      "<header2>Server<end>\n",
      "{servers}\n",
      "<header2>Abonnierte Channel<end>\n",
      "{subs}",
      "\n\nDas Discord Modul wurde von <highlight>Vladimirovna<end> geschrieben\n"
    ]
  },
  "blob_relay": {
    "en_US": [
      "<header2>Info<end>\n",
      "Status: {connected} [{switch_connection}]\n",
      "Channels available: <highlight>{count}<end>\n\n",
      "<header2>Subscription setup<end>\n",
      "{subs}",
      "\n\nDiscord Module written by <highlight>Vladimirovna<end>\n"
    ],
    "de_DE": [
      "<header2>Informationen<end>\n",
      "Status: {connected} [{switch_connection}]\n",
      "Verfügbare Channel: <highlight>{count}<end>\n\n",
      "<header2>Abonnierte Channel<end>\n",
      "{subs}",
      "\n\nDas Discord Modul wurde von <highlight>Vladimirovna<end> geschrieben\n"
    ]
  },

  "connected": {
    "en_US": "<green>Connected<end>",
    "de_DE": "<green>Verbunden<end>"
  },
  "disconnected": {
    "en_US": "<red>Disconnected<end>",
    "de_DE": "<red>Verbindung getrennt<end>"
  },
  "connect": {
    "en_US": "<green>Connect<end>",
    "de_DE": "<green>Verbinden<end>"
  },
  "disconnect": {
    "en_US": "<red>Disconnect<end>",
    "de_DE": "<red>Verbindung trennen<end>"
  },
  "server": {
    "en_US": [
      "{server_name} [{invite}]\n",
      " └ member count: {m_count}\n",
      " └ owner: {owner}\n\n"
    ],
    "de_DE": [
      "{server_name} [{invite}]\n",
      " └ Anzahl der Mitglieder: {m_count}\n",
      " └ Inhaber: {owner}\n\n"
    ]
  },
  "get_invite": {
    "en_US": "get invite",
    "de_DE": "Einladung erhalten"
  },
  "no_server": {
    "en_US": "None\n\n",
    "de_DE": "Keine Server vorhanden\n\n"
  },
  "sub": {
    "en_US": [
      "<highlight>{server_name}<end> :: <highlight>{channel_name}<end>\n",
      " └ relaying from AO [{relay_ao}]\n",
      " └ relaying from Discord [{relay_dc}]\n"
    ],
    "de_DE": [
      "<highlight>{server_name}<end> :: <highlight>{channel_name}<end>\n",
      " └ Weiterleitung vom AO Chat ist [{relay_ao}]\n",
      " └ Weiterleitung vom Discord Chat ist [{relay_dc}]\n"
    ]
  },
  "relay": {
    "en_US": [
      "<highlight>{server_name}<end> :: <highlight>{channel_name}<end>\n",
      " └ relaying from AO [{relay_ao}] [{switch_ao}]\n",
      " └ relaying from Discord [{relay_dc}] [{switch_dc}]\n"
    ],
    "de_DE": [
      "<highlight>{server_name}<end> :: <highlight>{channel_name}<end>\n",
      " └ Weiterleitung vom AO Chat ist [{relay_ao}] [{switch_ao}]\n",
      " └ Weiterleitung vom Discord Chat ist [{relay_dc}] [{switch_dc}]\n"
    ]
  },
  "title": {
    "en_US": "Discord Info",
    "de_DE": "Discord Informationen"
  },
  "no_perms": {
    "en_US": "Insufficient permissions",
    "de_DE": "Unzureichende Rechte"
  },
  "on": {
    "en_US": "<green>On<end>",
    "de_DE": "<green>An<end>"
  },
  "off": {
    "en_US": "<red>Off<end>",
    "de_DE": "<red>Aus<end>"
  },
  "already_connected": {
    "en_US": "Discord is already connected.",
    "de_DE": "Es besteht bereits eine Verbindung zu Discord."
  },
  "connect_success": {
    "en_US": "Connected to Discord successfully.",
    "de_DE": "Verbindung zu Discord erfolgreich hergestellt."
  },
  "no_token": {
    "en_US": "Cannot connect to Discord, no bot token is set.",
    "de_DE": "Es ist kein bot token hinterlegt, wodurch ich keine Verbindung zu Discord herstellen kann."
  },
  "not_connected": {
    "en_US": "Discord is not connected.",
    "de_DE": "Es besteht keine Verbindung zu Discord."
  },
  "disconnect_msg": {
    "en_US": "Disconnected from Discord successfully.",
    "de_DE": "Die Verbindung zu Discord wurde erfolgreich beendet."
  },
  "unknown_relay_type": {
    "en_US": "Unknown relay type.",
    "de_DE": "Unbekannter Relay Typ."
  },
  "changed_relay": {
    "en_US": "Changed Relay for {channel} to {changed}",
    "de_DE": "Die Weiterleitung des Channels {channel} ist nun {changed}"
  },
  "no_dc": {
    "en_US": "Could not find Discord server with ID <highlight>{id}<end>.",
    "de_DE": "Es konnte kein Discord Server mit der ID <highlight>{id}<end> gefunden werden."
  },
  "blob_invites": {
    "en_US": [
      "<header2>Available invites<end>\n",
      "{invites}\n"
    ],
    "de_DE": [
      "<header2> Verfügbare Einladungen<end>\n",
      "{invites}\n"
    ]
  },
  "invite": {
    "en_US": [
      "{server} [{link}]\n",
      " └ life time: {time_left}\n",
      " └ used: {count_used}\n",
      " └ uses left: {count_left}\n",
      "{channel}\n\n"
    ],
    "de_DE": [
      "{server} [{link}]\n",
      " └ Verbleibende Lebenszeit: {time_left}\n",
      " └ Verwendet: {count_used}\n",
      " └ Verbleibende Verwendungen: {count_left}\n",
      "{channel}\n\n"
    ]
  },
  "no_invites": {
    "en_US": "None available, maybe the bot user does not have sufficient permissions to see invites, or no invites exists.\\n\\n",
    "de_DE": ""
  },
  "join": {
    "en_US": "join",
    "de_DE": "Beitreten"
  },
  "inv_channel": {
    "en_US": " └ for channel: {channel}",
    "de_DE": " └ für den Channel: {channel}"
  },
  "invite_title": {
    "en_US": "Discord invites",
    "de_DE": "Discord Einladungen"
  },
  "relay_title": {
    "en_US": "Discord Relay",
    "de_DE": "Discord Weiterleitungen"
  }


}
