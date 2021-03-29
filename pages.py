from otree.api import Currency as c, currency_range
from ._builtin import Page, WaitPage
from .models import Constants
from .project_logger import get_logger
from .trading_tools import bot_attempted_trade

logger = get_logger('pages.py')

# Description of the game: How to play and returns expected
class Introduction(Page):
    logger.debug("-> Entering Introduction")

    def is_displayed(self):
        return self.round_number == 1 and self.participant.vars['MobilePhones'] is False

    def vars_for_template(self):
        exchange_rate = self.session.config['real_world_currency_per_point']
        players_per_group = Constants.players_per_group
        foreign_tax = self.session.config['foreign_tax']
        perc_f_tax_consumer = self.session.config['percent_foreign_tax_consumer']
        perc_f_tax_producer = self.session.config['percent_foreign_tax_producer']
        store_cost_hom = self.session.config['token_store_cost_homogeneous']
        store_cost_het = self.session.config['token_store_cost_heterogeneous']
        show_foreign_transactions = self.session.config['show_foreign_transactions']

        # Treatment variable: 0 if baseline, 1 if tax treatment, 2 if cost treatment, 3 show foreign trans treatment
        # Baseline Treatment
        perc_taxes = False
        storage_costs = False

        logger.info(f"perc_f_tax_consumer = {perc_f_tax_consumer}, perc_f_tax_producer = {perc_f_tax_producer}")
        logger.info(f"store_cost_hom = {store_cost_hom}, store_cost_het = {store_cost_het}")

        # Tax Treatment
        if perc_f_tax_consumer != 0 or perc_f_tax_producer != 0:
            perc_taxes = True
        # 2 Cost Treatment
        if store_cost_hom != 0 or store_cost_het != 0:
            storage_costs = True

        tax_producer = perc_f_tax_producer * round(foreign_tax,1)
        tax_consumer = perc_f_tax_consumer * round(foreign_tax,1)

        return dict(participant_id=self.participant.label, exchange_rate=exchange_rate, players_per_group=players_per_group,
                    perc_f_tax_consumer=perc_f_tax_consumer,
                    perc_f_tax_producer=perc_f_tax_producer, foreign_tax=foreign_tax, store_cost_hom=store_cost_hom,
                    store_cost_het=store_cost_het, show_foreign_transactions=show_foreign_transactions,
                    perc_taxes=perc_taxes, storage_costs=storage_costs,
                    tax_producer=tax_producer, tax_consumer=tax_consumer)
    logger.debug("<- Exiting Introduction")


class Trade(Page):
    logger.debug("-> Entering Trade")

    timeout_seconds = 60
    form_model = 'player'
    form_fields = ['trade_attempted', 'trading']

    def vars_for_template(self):
        # self.session.vars['pairs'] is a list of rounds.
        # each round is a dict of (group,id):(group,id) pairs.
        logger.debug("58: player telling bots to trade")
        logger.info(f"Current Round is {self.round_number}")
        group_id = self.player.participant.vars['group']
        player_groups = self.subsession.get_groups()
        logger.info(f"Player Groups {player_groups}")
        bot_players = self.session.vars['automated_traders'][f"round_{self.round_number}"]
        logger.info(f"Bot Groups {bot_players}")

        # special case: one special player gets to tell all the bots paired
        # with other bots, to trade

        #TODO: erase after refactoring
        # # only if the automated trader treatment is on
        # if self.session.config['automated_traders']:
        #     logger.info(f"70: Current player = {self.player.id_in_group}")
        #     if group_id == 0 and self.player.id_in_group == 1:
        #         for t1, t2 in self.session.vars['pairs'][self.round_number - 1].items():
        #             logger.info(f"73: t1 is {t1} and t2 is {t2}")
        #             t1_group, t1_id = t1
        #             t2_group, _ = t2
        #             # if both members of the pair are bots
        #             logger.info(f"77: t1_group is {t1_group} and t2_group is {t2_group}")
        #             logger.info(f"78: bot groups = {bot_groups}")
        #             if t1_group >= len(player_groups) and t2_group >= len(player_groups):
        #                 a1 = bot_groups[(t1_group, t1_id)]
        #                 a1.trade(self.subsession)

        # gets a another pair
        # the other pair is the pair that is paired with the current player
        # if self.session.config['custom_matching'] is True: # id_in_group used directly
        #     other_group, other_id = self.session.vars['pairs'][self.round_number - 1][
        #         (group_id, self.player.id_in_group)]
        # else: # index used instead of id_in_group
        logger.debug("89: gets a another pair")
        other_group, other_id = self.session.vars['pairs'][self.round_number - 1][
            (group_id, self.player.id_in_group - 1)]

        logger.info(f"91: Other group = {other_group}")
        if other_group < len(player_groups): # for human player partners
            logger.info(f"other_group < len(player_groups) = {other_group < len(player_groups)}")
            other_player = player_groups[other_group].get_player_by_id(other_id + 1)
            logger.info(f"other normal player = {other_player}")
        
        else: # for bots partners
            logger.info(f"other_group < len(player_groups) = {other_group < len(player_groups)}")
            other_player = bot_players[(other_group, other_id)]
            logger.info(f"other bot player = {other_player}")

        self.player.my_id_in_group = self.player.id_in_group
        logger.info(f"Player id in group = {self.player.id_in_group}")
        self.player.my_group_id = group_id
        logger.info(f"Player group id = {group_id}")
        self.player.other_id_in_group = other_id + 1
        logger.info(f"Player other id in group = {self.player.other_id_in_group}")
        self.player.other_group_id = other_group
        logger.info(f"Player other group id = {other_group}")

        # whatever color token they were assigned in models.py
        self.player.token_color = self.player.participant.vars['token']

        #TODO: add conditional for bot and human players. if bot, extract required data from matching file or else
        if other_group < len(player_groups): # for human player partners
            self.player.other_token_color = other_player.participant.vars['token']
            self.player.other_group_color = other_player.participant.vars['group_color']
        else: # for bots partners
            self.player.other_token_color = other_player['token']
            self.player.other_group_color = other_player['group_color']

        # defining roles as in models.py
        # ensuring opposites, such that half are producers and half are consumers
        self.player.role_pre = 'Consumer' if self.player.participant.vars['token'] != Constants.trade_good else 'Producer'
        self.player.other_role_pre = 'Consumer' if self.player.other_token_color != Constants.trade_good else 'Producer'

        # defining group color as in models.py
        self.player.group_color = self.player.participant.vars['group_color']

        # defining the variables for the instructions template
        exchange_rate = self.session.config['real_world_currency_per_point']
        players_per_group = Constants.players_per_group
        foreign_tax = self.session.config['foreign_tax']
        perc_f_tax_consumer = self.session.config['percent_foreign_tax_consumer']
        perc_f_tax_producer = self.session.config['percent_foreign_tax_producer']
        store_cost_hom = self.session.config['token_store_cost_homogeneous']
        store_cost_het = self.session.config['token_store_cost_heterogeneous']
        show_foreign_transactions = self.session.config['show_foreign_transactions']
        tax_producer = round(perc_f_tax_producer, 1) * foreign_tax
        tax_consumer = round(perc_f_tax_consumer, 1) * foreign_tax

        # Treatment variable: 0 if baseline, 1 if tax treatment, 2 if cost treatment, 3 show foreign trans treatment
        # Baseline Treatment
        treatment = 0
        # Tax Treatment
        if perc_f_tax_consumer != 0 and perc_f_tax_producer != 0 and foreign_tax != 0:
            treatment = 1
        # 2 Cost Treatment
        elif store_cost_hom != 0 or store_cost_het != 0:
            treatment = 2
        # 3 Show Foreign Trans Treatment
        elif show_foreign_transactions is True:
            treatment = 3

        return {'participant_id': self.participant.label,
            'role_pre': self.player.role_pre,
            'other_role_pre': self.player.other_role_pre,
            'token_color': self.player.participant.vars['token'],
            'group_color': self.player.participant.vars['group_color'],
            'other_token_color': self.player.other_token_color,
            'other_group_color': self.player.other_group_color,
            'exchange_rate': exchange_rate,
            'players_per_group': players_per_group,
            'perc_f_tax_consumer': perc_f_tax_consumer,
            'perc_f_tax_producer': perc_f_tax_producer,
            'foreign_tax': foreign_tax,
            'store_cost_hom': store_cost_hom,
            'store_cost_het': store_cost_het,
            'show_foreign_transactions': show_foreign_transactions,
            'treatment': treatment,
            'tax_producer': tax_producer,
            'tax_consumer': tax_consumer
            }

    def before_next_page(self):
        if self.round_number == 1: # defining the participant var at 1st round
            self.participant.vars["total_timeouts"] = 0

        if self.timeout_happened:
            self.player.player_timed_out += 1
            ########33## TESTING PURPOSES ONLY
            #if self.player.role_pre != self.player.other_role_pre:
            #    self.player.trade_attempted = True
            #else:
            #    self.player.trade_attempted = False

            ###### END TESTING PURPOSES ONLY
            #TODO: Erase after debugging
            self.player.trade_attempted = True
        
        # counting the total timeouts until this moment
        self.participant.vars["total_timeouts"] += self.player.player_timed_out

    def is_displayed(self):
        return self.participant.vars['MobilePhones'] is False and self.round_number <= self.session.vars['predetermined_stop']
    
    logger.debug("<- Exiting Trade")


class ResultsWaitPage(WaitPage):
    logger.debug("-> Entering ResultsWaitPage")

    body_text = 'Espere a que los otros participantes terminen de decidir'
    # wait_for_all_groups = True

    def after_all_players_arrive(self):
        pass

    def is_displayed(self):
        return self.participant.vars['MobilePhones'] is False and self.round_number <= self.session.vars['predetermined_stop']
    
    logger.debug("<- Exiting ResultsWaitPage")


class Results(Page):
    logger.debug("-> Entering Results")

    timeout_seconds = 1

    def vars_for_template(self):
        group_id = self.player.participant.vars['group'] 
        player_groups = self.subsession.get_groups()
        bot_players = None # placeholder for bot player's data in round
        bot_players_next_round = None # placeholder for bot player's data in next round

        # special case: one special player gets to tell all the bots paired
        # with other bots, to compute results
        logger.info(f"213: automated_traders is {self.session.config['automated_traders']}")
        if self.session.config['automated_traders']:
            
            bot_players = self.session.vars['automated_traders'][f"round_{self.round_number}"]
            bot_players_next_round = self.session.vars['automated_traders'][f"round_{self.round_number + 1}"]
            bot_attempted_transactions = {} # attempted transactions in current round for all bots

            for bot_key in bot_players.keys():
                bot_attempted_transactions[bot_key] = None

            logger.info(f"group_id = {group_id}, self.player.id_in_group = {self.player.id_in_group}")
            if group_id == 0 and self.player.id_in_group == 1: 

                for t1, t2 in self.session.vars['pairs'][self.round_number - 1].items():
                    t1_group, t1_id = t1
                    t2_group, t2_id = t2

                    # if both members of the pair are bots
                    logger.info(f"224: t1_group = {t1_group}, t2_group = {t2_group}")
                    if t1_group >= len(player_groups) and t2_group >= len(player_groups):
                        # current round players
                        a1 = bot_players[(t1_group, t1_id)]
                        a2 = bot_players[(t2_group, t2_id)]

                        # current round token
                        a1_token = a1["token"]
                        a2_token = a2["token"]

                        # next round players
                        a1_next_round = bot_players_next_round[(t1_group, t1_id)]
                        a2_next_round = bot_players_next_round[(t2_group, t2_id)]

                        # next round token
                        a1_token_next_round = a1_next_round["token"]
                        a2_token_next_round = a2_next_round["token"]

                        # registering each attempted trade        
                        if bot_attempted_transactions[(t1_group, t1_id)] == None:
                            bot_attempted_transactions[(t1_group, t1_id)] = bot_attempted_trade(a1_token, a2_token)

                        if bot_attempted_transactions[(t2_group, t2_id)] == None:
                            bot_attempted_transactions[(t2_group, t2_id)] = bot_attempted_trade(a2_token, a1_token)
                        
                        # given that both are bots, only item switching'll be done
                        trade_succeeded = bot_attempted_transactions[(t1_group, t1_id)] and \
                                          bot_attempted_transactions[(t2_group, t2_id)]
                        if trade_succeeded:
                            a1_token_next_round = a2_token
                            a2_token_next_round = a1_token
       
        # identify trading partner
        # similar to above in Trade()
        # if self.session.config['custom_matching'] is True: # id_in_group used directly
        #     other_group, other_id = self.session.vars['pairs'][self.round_number - 1][
        #         (group_id, self.player.id_in_group)]
        # else: # index used instead of id_in_group
        logger.debug("235: identify trading partner")
        other_group, other_id = self.session.vars['pairs'][self.round_number - 1][
            (group_id, self.player.id_in_group - 1)]
        
        # get other player object (for humans)
        logger.info(f"other_group = {other_group}, len(player_groups) = {len(player_groups)}")
        other_player_trade_attempted = None # placeholder for attempting trade
        if other_group < len(player_groups):
            other_player = player_groups[other_group].get_player_by_id(other_id + 1)
            other_player_trade_attempted = other_player.trade_attempted
        #TODO: human bot trade refactoring
        else:
            other_player = bot_players[(other_group, other_id)]
            other_player_next_round = bot_players_next_round[(other_group, other_id)]
            other_player_item = other_player["token"]
            print(f"DEBUG: Player next round data {other_player_next_round}")
            other_player_item_next_round = other_player_next_round["token"]
            other_player_trade_attempted = bot_attempted_trade(other_player_item, self.player.participant.vars['token'])
            
        # define initial round payoffs
        round_payoff = c(0)

        # logic for switching objects on trade
        # if both players attempted a trade, it must be true
        # that one is a producer and one is a consumer.
        # Only 1 player performs the switch
        logger.info(f"254: self.player.trade_attempted = {self.player.trade_attempted}")
        logger.info(f"255: other_player.trade_attempted = {other_player_trade_attempted}")
        
        if self.player.trade_attempted and other_player_trade_attempted: 

            # only 1 player actually switches the goods
            logger.info(f"259: self.player.trade_succeeded is {self.player.trade_succeeded}")
            logger.info(f"round number = {self.round_number}")
            logger.info(f"id in group = {self.player.id_in_group}")
            # logger.info(f"other id in group = {other_player.id_in_group}")
            if self.player.trade_succeeded is None:

                # switch tokens
                if other_group < len(player_groups): # for humans
                    self.player.participant.vars['token'] = self.player.other_token_color
                    other_player.participant.vars['token'] = self.player.token_color    
                    other_player.trade_succeeded = True
                else: # for bots
                    # next round token
                    self.player.participant.vars['token'] = other_player_item
                    other_player_item_next_round = self.player.token_color
                    # bots don't have trade_succeeded var

                # set players' trade_succeeded field
                self.player.trade_succeeded = True
                

            ### TREATMENT: TAX ON FOREIGN (OPPOSITE) CURRENCY
            # if the player is the consumer, apply consumer tax to them
            # and apply producer tax to other player

            # FOREIGN TRANSACTION:
            # added condition that both parties the same group color
            logger.info(f"self.player.role_pre is {self.player.role_pre}")
            if self.player.role_pre == 'Consumer':

                tax_consumer = c(0)
                logger.info(f"tax_consumer = {tax_consumer}")
                logger.info(f"self.player.token_color = {self.player.token_color}")
                logger.info(f"self.player.other_group_color = {self.player.other_group_color}")
                logger.info(f"self.player.group_color = {self.player.group_color}")
                logger.info(f"self.session.config['foreign_tax'] = {self.session.config['foreign_tax']}")
                logger.info(f"self.session.config['percent_foreign_tax_consumer'] = {self.session.config['percent_foreign_tax_consumer']}")
                if self.player.token_color != self.player.other_group_color and \
                        self.player.group_color == self.player.other_group_color:
                    tax_consumer += self.session.config['foreign_tax'] \
                        * round(self.session.config['percent_foreign_tax_consumer'], 1)
                    logger.info(f"tax_consumer after change = {tax_consumer}")
                    self.player.tax_paid = tax_consumer
                    logger.info(f"self.player.tax_paid consumer = {self.player.tax_paid}")
                round_payoff += Constants.reward - tax_consumer
                logger.info(f"new round_payoff consumer = {round_payoff}")
                

            # else if the player is the consumer, opposite
                
            else:
                logger.debug("else if the player is the consumer, opposite")
                tax_producer = c(0)
                logger.info(f"tax_producer = {tax_producer}")
                logger.info(f"self.player.token_color = {self.player.token_color}")
                logger.info(f"self.player.other_group_color = {self.player.other_group_color}")
                logger.info(f"self.player.group_color = {self.player.group_color}")
                logger.info(f"self.session.config['foreign_tax'] = {self.session.config['foreign_tax']}")
                logger.info(f"self.session.config['percent_foreign_tax_producer'] = {self.session.config['percent_foreign_tax_producer']}")
                if self.player.group_color != self.player.other_token_color and \
                        self.player.group_color == self.player.other_group_color:
                    tax_producer += self.session.config['foreign_tax'] \
                        * round(self.session.config['percent_foreign_tax_producer'], 1)
                    logger.info(f"tax_producer = {tax_producer}")
                    self.player.tax_paid = tax_producer
                    logger.info(f"self.player.tax_paid producer = {self.player.tax_paid}")
                round_payoff -= tax_producer
                logger.info(f"new round_payoff producer = {round_payoff}")

        else:
            self.player.trade_succeeded = False

        # penalties for self
        # if your token matches your group color

        # TOKEN STORE COST:
        # if token held for a round = if trade did not succeed
        # homo: token is your color
        # hetero: token is different color
        logger.info(f"318: self.player.trade_succeeded is {self.player.trade_succeeded}")
        if not self.player.trade_succeeded:

            logger.info(f"self.player.participant.vars['token'] = {self.player.participant.vars['token']}")
            logger.info(f"self.participant.vars['group_color'] = {self.participant.vars['group_color']}")
            logger.info(f"self.player.group_color = {self.player.group_color}")
            if self.player.participant.vars['token'] == self.participant.vars['group_color']:
                round_payoff -= c(self.session.config['token_store_cost_homogeneous'])
                self.player.storage_cost_paid = self.session.config['token_store_cost_homogeneous']

            elif self.player.participant.vars['token'] != Constants.trade_good:
                round_payoff -= c(self.session.config['token_store_cost_heterogeneous'])
                self.player.storage_cost_paid = self.session.config['token_store_cost_heterogeneous']

        # set payoffs
        self.player.set_payoffs(round_payoff)
        if self.player.trade_succeeded:
            new_token_color = self.player.other_token_color
        else:
            new_token_color = self.player.token_color
            
        #TODO: erase after refactoring
        # tell bot to compute its own trade
        # if self.session.config['automated_traders'] == True \
        #         and other_group >= len(player_groups):
        #     other_player.compute_results(self.subsession, Constants.reward)

        return {'participant_id': self.participant.label,
            'token_color': self.player.token_color,
            'other_token_color': self.player.other_token_color,
            'role_pre': self.player.role_pre,
            'other_role_pre': self.player.other_role_pre,
            'trade_attempted': self.player.trade_attempted,
            'group_color': self.player.group_color,
            'trade_succeeded': self.player.trade_succeeded,
            'new_token_color': new_token_color,
            'round_payoff': self.player.payoff,
            'round_number': self.round_number, 
        }

    def is_displayed(self):
        return self.participant.vars['MobilePhones'] is False and self.round_number <= self.session.vars['predetermined_stop']

    logger.debug("-> Exiting Results")  


class PostResultsWaitPage(WaitPage):
    logger.debug("-> Entering PostResultsWaitPage")

    body_text = 'Waiting for other participants to finish viewing results.'
#    wait_for_all_groups = True

    def after_all_players_arrive(self):
        bot_players = self.session.vars['automated_traders']
        
        # count foreign currency transactions this round
        fc_count = 0
        fc_possible_count = 0

        logger.debug("376: count foreign currency transactions this round")
        for p in self.subsession.get_players():
            logger.info("p.group_color = {p.group_color}, p.other_group_color = {p.other_group_color}, p.role_pre = {p.role_pre}")
            if p.group_color == p.other_group_color and \
                    p.group_color != p.other_token_color and \
                    p.role_pre == 'Producer':
                if p.trade_attempted:
                    fc_count += 1
                    fc_possible_count += 1
                else:
                    fc_possible_count += 1

        #for b in bot_groups.values():
       #     if b.group_color == b.other_group_color and \
       #             b.group_color != b.other_token_color and \
       #             b.role_pre == 'Producer':
       #         if b.trade_attempted:
       #             fc_count += 1
       #             fc_possible_count += 1
       #         else:
       #             fc_possible_count += 1

        self.subsession.fc_transactions = fc_count
        self.subsession.possible_fc_transactions = fc_possible_count

        # Changes added to make the game show "N.A." in case the denominator for the fc_percent is 0
        # In order to return quickly to the original version in case an error appears, the eli code is on comments
        # To make this work, the fc_transaction_percent field was changed to String

        # if fc_count > 0 and fc_possible_count > 0:
        if fc_possible_count > 0:
            fc_percent = int((fc_count / fc_possible_count)*100)
            self.subsession.fc_transaction_percent = f'{fc_percent}%'
        else:
            self.subsession.fc_transaction_percent = ''#'N.A.'

        """
        fc_percent = 0
        if fc_count > 0 and fc_possible_count > 0:
            fc_percent = fc_count/fc_possible_count
        self.subsession.fc_transaction_percent = int(fc_percent*100)
        """

        # if self.subsession.round_number == Constants.num_rounds:
        #     for bot in bot_groups.values():
        #         bot.export_data()
            # for p in self.subsession.get_players():
            #    p.participant.payoff *= self.session.config['soles_per_ecu']

    def is_displayed(self):
        return self.participant.vars['MobilePhones'] is False and self.round_number <= self.session.vars['predetermined_stop']

    logger.debug("<- Exiting PostResultsWaitPage")


class FinalResults(Page):
    logger.debug("-> Entering FinalResults")

    def vars_for_template(self):
        self.player.total_timeouts = self.participant.vars["total_timeouts"]
        self.player.total_discounts = self.player.total_timeouts*c(1)
        
        # converting points to real money
        payoff_money = self.participant.payoff.to_real_world_currency(self.player.session)
        total_discounts_money = self.player.total_discounts.to_real_world_currency(self.player.session)

        return {'participant_id': self.participant.label,
                "participation_fee": self.session.config["participation_fee"],
                "payoff_money": payoff_money,
                "total_timeouts": self.player.total_timeouts,
                "total_discounts_points": self.player.total_discounts,
                "total_discounts_money": total_discounts_money}

    def is_displayed(self):
        return self.round_number == Constants.num_rounds

    def before_next_page(self):
        self.player.payoff -= self.player.total_discounts # discounting 1 point
    
    logger.debug("<- Exiting FinalResults")

page_sequence = [
    Trade,
    ResultsWaitPage,
    Results,
    PostResultsWaitPage,
    FinalResults
]
