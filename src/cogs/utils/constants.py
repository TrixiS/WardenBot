

class TagsConstants:

    MAX_LEN = 60
    CHECK_PAGE_MAX = 30


class RanksConstants:

    ROLE_NAME_MAX_LEN = 68
    ROLES_MAX_COUNT = 30


class EmbedConstants:

    TITLE_MAX_LEN = 256
    DESC_MAX_LEN = 2048
    FIELD_MAX_COUNT = 25
    FIELD_NAME_MAX_LEN = 256
    FIELD_VALUE_MAX_LEN = 1024
    FOOTER_TEXT_MAX_LEN = 2048
    AUTHOR_NAME_MAX_LEN = 256


class StringConstants:

    DOT_SYMBOL = '•'
    ALLOWED_FMT_FIELDS = (
        "created_at",
        "name", "id",
        "mention"
    )


class ModerationConstants:

    CASES_PER_PAGE = 10
    PURGE_LIMIT = 1000


class EconomyConstants:

    DEFAULT_SYMBOL = ':dollar:'
    USER_PER_PAGE = 10
    STORY_MAX_LEN = 1500
    SLOTS = (
        '🍇', '🍈', '🍉', 
        '🍊', '🍋', '🍌', 
        '🍍', '🥭', '🍎', 
        '🍏', '🍐', '🍑',
        '🍒', '🍓', '🥝',
        '🍅', '🥥', '🥑',
        '🍆', '🥔', '🥕', 
        '🌽', '🌶', '🥒', 
        '🥬', '🥦', '🍄', 
        '🥜', '🌰'
    )
    ROLLS = {
        1: "<:d1:693091317856862280>",
        2: "<:d2:693091317781233675>",
        3: "<:d3:693091318301458452>",
        4: "<:d4:693091317768781876>",
        5: "<:d5:693091317919514665>",
        6: "<:d6:693091318150201455>"
    }


class TwitchAlertsConstants:

    USER_PER_PAGE = 30


class FunConstants:

    ATTACH_MAX_SIZE = 1000000
    REX_API_URL = "https://rextester.com/rundotnet/api"
    DOG_API_URL = "https://dog.ceo/api/breeds/image/random"
    SPELLER_API_URL = "https://speller.yandex.net/services/spellservice.json/checkText"
    IMAGE_API_URL = "https://www.colorbook.io/imagecreator.php/?"


class InfoConstants:

    GHUB_API_URL = "https://api.github.com"
    BOT_INVITE_URL = "https://discordapp.com/api/oauth2/authorize?client_id={}&permissions=8&scope=bot"