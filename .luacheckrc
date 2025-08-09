std = 'lua51'
max_line_length = false
exclude_files = {'**Libs/', '**libs/'}
ignore = {
    '11./SLASH_.*', -- Setting an undefined (Slash handler) global variable
    '11./BINDING_.*', -- Setting an undefined (Keybinding header) global variable
    '113/LE_.*', -- Accessing an undefined (Lua ENUM type) global variable
    '113/NUM_LE_.*', -- Accessing an undefined (Lua ENUM type) global variable
    '211', -- Unused local variable
    '211/L', -- Unused local variable "L"
    '211/CL', -- Unused local variable "CL"
    '212', -- Unused argument
    '213', -- Unused loop variable
    '214', -- Unused hint
    -- '231', -- Set but never accessed
    '311', -- Value assigned to a local variable is unused
    '314', -- Value of a field in a table literal is unused
    '42.', -- Shadowing a local variable, an argument, a loop variable.
    '43.', -- Shadowing an upvalue, an upvalue argument, an upvalue loop variable.
    '542', -- An empty if branch
    '581', -- Error-prone operator orders
    '582', -- Error-prone operator orders
}

globals = {
    "101_CutsceneName_Ref",
    "101_CutsceneName_Ref2",
    "10_1_5_TIME_RIFTS_MINIGAME_01_WRONG_ELEMENT",
    "10_1_5_TIME_RIFTS_MINIGAME_02_UNCROSS_TIMELINES",
    "10_1_5_TIME_RIFTS_MINIGAME_03_ADJUST_HOURGLASS",
    "10_1_5_TIME_RIFTS_MINIGAME_04_FLYING_SAND",
    "10_1_5_TIME_RIFTS_MINIGAME_05_FALLING_SAND",
    "10_1_5_TIME_RIFTS_MINIGAME_06A_SELECT_MATCHING_MURLOC",
    "10_1_5_TIME_RIFTS_MINIGAME_06B_SELECT_MATCHING_TITAN",
    "10_1_5_TIME_RIFTS_MINIGAME_06C_SELECT_MATCHING_SCOURGE",
    "10_1_5_TIME_RIFTS_MINIGAME_06D_SELECT_MATCHING_DEMON",
    "10_1_5_TIME_RIFTS_MINIGAME_06E_SELECT_MATCHING_BLACK_EMPIRE",
    "10_1_5_TIME_RIFTS_MINIGAME_06F_SELECT_MATCHING_HvA",
    "10_1_5_TIME_RIFTS_MINIGAME_06G_SELECT_MATCHING_ROBOT",
    "11.1.7 Lorewalking - Restart (LAS)",
    "11_0_0_DELVES_MINIGAME_01",
    "11_0_7_kirintor_bomb",
    "11_0_Z_1_MAX_CAMPAIGN_MINIGAME_REWIRE",
    "11_0_Z_1_WQ_MINIGAME_01_ARCANE_LOCK",
    "20th_ANNIVERSARY_THEME_01_01",
    "20th_ANNIVERSARY_THEME_01_02",
    "20th_ANNIVERSARY_THEME_01_03",
    "20th_ANNIVERSARY_THEME_01_04",
    "20th_ANNIVERSARY_THEME_01_05",
    "20th_ANNIVERSARY_THEME_02_01",
    "20th_ANNIVERSARY_THEME_02_02",
    "20th_ANNIVERSARY_THEME_02_03",
    "20th_ANNIVERSARY_THEME_02_04",
    "20th_ANNIVERSARY_THEME_02_05",
    "20th_ANNIVERSARY_THEME_03_01",
    "20th_ANNIVERSARY_THEME_03_02",
    "20th_ANNIVERSARY_THEME_03_03",
    "20th_ANNIVERSARY_THEME_03_04",
    "20th_ANNIVERSARY_THEME_03_05",
    "20th_ANNIVERSARY_THEME_04_01",
    "20th_ANNIVERSARY_THEME_04_02",
    "20th_ANNIVERSARY_THEME_04_03",
    "20th_ANNIVERSARY_THEME_04_04",
    "20th_ANNIVERSARY_THEME_04_05",
    "20th_ANNIVERSARY_THEME_05_01",
    "20th_ANNIVERSARY_THEME_05_02",
    "20th_ANNIVERSARY_THEME_05_03",
    "20th_ANNIVERSARY_THEME_05_04",
    "20th_ANNIVERSARY_THEME_05_05",
    "20th_ANNIVERSARY_THEME_06_01",
    "20th_ANNIVERSARY_THEME_06_02",
    "20th_ANNIVERSARY_THEME_06_03",
    "20th_ANNIVERSARY_THEME_06_04",
    "20th_ANNIVERSARY_THEME_06_05",
    "20th_ANNIVERSARY_THEME_07_01",
    "20th_ANNIVERSARY_THEME_07_02",
    "20th_ANNIVERSARY_THEME_07_03",
    "20th_ANNIVERSARY_THEME_07_04",
    "20th_ANNIVERSARY_THEME_07_05",
    "20th_ANNIVERSARY_THEME_08_01",
    "20th_ANNIVERSARY_THEME_08_02",
    "20th_ANNIVERSARY_THEME_08_03",
    "20th_ANNIVERSARY_THEME_08_04",
    "20th_ANNIVERSARY_THEME_08_05",
    "8.0_WARFRONTS_-_ARATHI_-_CONSTRUCT_BUILDING_-_BARRACKS",
    "82_TAUREN_HERITAGE_TOY_ERROR",
    "90POA_BOSS_01",
    "90POA_BOSS_02",
    "90POA_BOSS_03",
    "90POA_BOSS_04",
    "90POA_BOSS_05",
    "90POA_BOSS_06",
    "90POA_BOSS_07",
    "90POA_BOSS_08",
    "90POA_BOSS_09",
    "90POA_BOSS_10",
    "AccountStateAccountCurrenciesLoaded",
    "AccountStateAccountFactionsLoaded",
    "AccountStateAccountItemsLoaded",
    "AccountStateAccountMappingLoaded",
    "AccountStateAccountNotificationsLoaded",
    "AccountStateAccountWowlabsLoaded",
    "AccountStateAchievementsLoaded",
    "AccountStateArchivedPurchasesLoaded",
    "AccountStateAuctionableTokensLoaded",
    "AccountStateBanktabSettingsLoaded",
    "AccountStateBattleNetAccountLoaded",
    "AccountStateBitVectorsLoaded",
    "AccountStateBpayAddLicenseObjectsLoaded",
    "AccountStateBpayDistributionObjectsLoaded",
    "AccountStateBpayProductitemObjectsLoaded",
    "AccountStateCharacterItemsLoaded",
    "AccountStateCharactersLoaded",
    "AccountStateCombinedQuestLogLoaded",
    "AccountStateConsumableTokensLoaded",
    "AccountStateCriteriaLoaded",
    "AccountStateCurrencyCapsLoaded",
    "AccountStateCurrencyTransferLogLoaded",
    "AccountStateDataElementsLoaded",
    "AccountStateDynamicCriteriaLoaded",
    "AccountStateFutureFeature01DataLoaded",
    "AccountStateItemCollectionsLoaded",
    "AccountStateLgVendorPurchaseLoaded",
    "AccountStateMountsLoaded",
    "AccountStatePerksHeldItemLoaded",
    "AccountStatePerksPastRewardsLoaded",
    "AccountStatePerksPendingPurchaseLoaded",
    "AccountStatePerksPendingRewardsLoaded",
    "AccountStatePetjournalInitialized",
    "AccountStatePurchasesLoaded",
    "AccountStateQuestCriteriaLoaded",
    "AccountStateQuestLogLoaded",
    "AccountStateRafActivityLoaded",
    "AccountStateRafBalanceLoaded",
    "AccountStateRafRewardsLoaded",
    "AccountStateRevokedRafRewardsLoaded",
    "AccountStateSettingsLoaded",
    "AccountStateTrialBoostHistoryLoaded",
    "AccountStateVasTransactionsLoaded",
    "AccountStateWarbandScenesLoaded",
    "AccountStateWarbandsLoaded",
    "BuffOverlay",
    "BuffOverlayBorderTemplateMixin",
    "BuffOverlayDB",
    "CreateAllAccountCurrenciesDone",
    "CreateAllAccountDynamicCriteriaDone",
    "CreateAllAccountFactionsDone",
    "CreateAllAccountItemsDone",
    "CreateAllAccountMappingDone",
    "CreateAllAccountNotificationsDone",
    "CreateAllAchievementsDone",
    "CreateAllArchivedPurchasesDone",
    "CreateAllAuctionableTokensDone",
    "CreateAllBanktabSettingsDone",
    "CreateAllBattlepetsDone",
    "CreateAllBitVectorsDone",
    "CreateAllBpayAddLicenseObjectsDone",
    "CreateAllBpayDistributionObjectsDone",
    "CreateAllBpayProductitemObjectsDone",
    "CreateAllCharacterItemsDone",
    "CreateAllCharactersDone",
    "CreateAllCombinedQuestLogEntriesDone",
    "CreateAllConsumableTokensDone",
    "CreateAllCriteriaDone",
    "CreateAllCurrencyTransferLogDone",
    "CreateAllCurrencycapsDone",
    "CreateAllDataElementsDone",
    "CreateAllFutureFeature01DataDone",
    "CreateAllItemCollectionItemsDone",
    "CreateAllLgVendorPurchaseDone",
    "CreateAllMountsDone",
    "CreateAllNone",
    "CreateAllPerkHeldItemsDone",
    "CreateAllPerkPastRewardsDone",
    "CreateAllPerkPendingPurchasesDone",
    "CreateAllPerkPendingRewardsDone",
    "CreateAllPurchasesDone",
    "CreateAllQuestCriteriaDone",
    "CreateAllQuestLogDone",
    "CreateAllRafActivitiesDone",
    "CreateAllRafBalanceDone",
    "CreateAllRafRewardsDone",
    "CreateAllRevokedRafRewardsDone",
    "CreateAllSettingsDone",
    "CreateAllTrialBoostHistoryDone",
    "CreateAllVasTransactionsDone",
    "CreateAllWarbandGroupsDone",
    "CreateAllWarbandScenesLoadedDone",
    "CreateAllWowlabsDataDone",
    "CreateObject",
    "ElvUF_Parent",
    "FrameXML",
    "GAME_LOCALE",
    "GlobalAPI",
    "LibStub",
    "LoadOnDemand",
    "LuaAPI",
    "Mixins",
    "None",
    "Scorpio",
    "WhisperCraft",
    "WhisperCraftDB",
    "handlers",
    "methods",
    Alpha = {
        fields = {
            "inherits",
        },
    },
    Animation = {
        fields = {
            "inherits",
        },
    },
    AnimationGroup = {
        fields = {
            "inherits",
        },
    },
    ArchaeologyDigSiteFrame = {
        fields = {
            "inherits",
        },
    },
    Blob = {
        fields = {
            "inherits",
        },
    },
    Browser = {
        fields = {
            "inherits",
        },
    },
    Button = {
        fields = {
            "inherits",
        },
    },
    CheckButton = {
        fields = {
            "inherits",
        },
    },
    Checkout = {
        fields = {
            "inherits",
        },
    },
    CinematicModel = {
        fields = {
            "inherits",
        },
    },
    ColorSelect = {
        fields = {
            "inherits",
        },
    },
    ControlPoint = {
        fields = {
            "inherits",
        },
    },
    Cooldown = {
        fields = {
            "inherits",
        },
    },
    DressUpModel = {
        fields = {
            "inherits",
        },
    },
    EditBox = {
        fields = {
            "inherits",
        },
    },
    FlipBook = {
        fields = {
            "inherits",
        },
    },
    FogOfWarFrame = {
        fields = {
            "inherits",
        },
    },
    Font = {
        fields = {
            "inherits",
        },
    },
    FontInstance = {
        fields = {
            "inherits",
        },
    },
    FontString = {
        fields = {
            "inherits",
        },
    },
    Frame = {
        fields = {
            "inherits",
        },
    },
    GameTooltip = {
        fields = {
            "inherits",
        },
    },
    Line = {
        fields = {
            "inherits",
        },
    },
    LineScale = {
        fields = {
            "inherits",
        },
    },
    LineTranslation = {
        fields = {
            "inherits",
        },
    },
    MaskTexture = {
        fields = {
            "inherits",
        },
    },
    MessageFrame = {
        fields = {
            "inherits",
        },
    },
    Minimap = {
        fields = {
            "inherits",
        },
    },
    Model = {
        fields = {
            "inherits",
        },
    },
    ModelScene = {
        fields = {
            "inherits",
        },
    },
    ModelSceneActor = {
        fields = {
            "inherits",
        },
    },
    MovieFrame = {
        fields = {
            "inherits",
        },
    },
    Object = {
        fields = {
            "inherits",
        },
    },
    OffScreenFrame = {
        fields = {
            "inherits",
        },
    },
    Path = {
        fields = {
            "inherits",
        },
    },
    PlayerModel = {
        fields = {
            "inherits",
        },
    },
    QuestPOIFrame = {
        fields = {
            "inherits",
        },
    },
    Region = {
        fields = {
            "inherits",
        },
    },
    Rotation = {
        fields = {
            "inherits",
        },
    },
    Scale = {
        fields = {
            "inherits",
        },
    },
    ScenarioPOIFrame = {
        fields = {
            "inherits",
        },
    },
    ScriptObject = {
        fields = {
            "inherits",
        },
    },
    ScriptRegion = {
        fields = {
            "inherits",
        },
    },
    ScrollFrame = {
        fields = {
            "inherits",
        },
    },
    SimpleHTML = {
        fields = {
            "inherits",
        },
    },
    Slider = {
        fields = {
            "inherits",
        },
    },
    StatusBar = {
        fields = {
            "inherits",
        },
    },
    TabardModel = {
        fields = {
            "inherits",
        },
    },
    Texture = {
        fields = {
            "inherits",
        },
    },
    TextureBase = {
        fields = {
            "inherits",
        },
    },
    TextureCoordTranslation = {
        fields = {
            "inherits",
        },
    },
    Translation = {
        fields = {
            "inherits",
        },
    },
    UnitPositionFrame = {
        fields = {
            "inherits",
        },
    },
    VertexColor = {
        fields = {
            "inherits",
        },
    },
    WidgetAPI = {
        fields = {
            "FrameScriptObject",
            "inherits",
        },
    },
    WorldFrame = {
        fields = {
            "inherits",
        },
    },
}
