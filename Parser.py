from Tokens import *
from Nodes import *


class Parser():
    def __init__(self, token_list: list):
        self.token_list = token_list
        self.pos = 0

    def consume(self, token_type):
        current_token = self.get_current_token()
        if current_token.type == token_type:
            self.advance()
            return current_token
        else:
            raise TypeError("The current token has an incorrect type: {} != {}".format(
                self.get_current_token().type, token_type))

    def get_current_token(self) -> Token:
        return self.token_list[self.pos]

    def advance(self) -> None:
        self.pos += 1

    def peek(self) -> Token:
        return self.token_list[self.pos+1]

    def parse_value(self) -> ValueNode:
        '''
        This parses a value out of the tokens, and returns a ValueNode
        A Value has the highest precedence
        Value: INTEGER | LPAREN expression RPAREN | FLOAT | ID | Keyword | FunctionCall
        '''
        if self.get_current_token().type == ID:
            if self.peek().type == LPAREN:
                return self.parse_functioncall()
            else:
                node = ValueNode(self.get_current_token())
                self.advance()
                return node   

        if self.get_current_token().type in NUMERIC:
            node = ValueNode(self.get_current_token())
            self.advance()
            return node

        if self.get_current_token().type == LPAREN:
            self.advance()  # In order to move into the parentheses
            node = self.parse_expression()
            self.advance()  # In order to move out of the parentheses
            return node

        if self.get_current_token().type == MINUS:
            self.advance()
            node = SingleNode(self.parse_value(), Token(MINUS, "-"))
            return node

        if self.get_current_token().type == BANG:
            self.advance()
            node = SingleNode(self.parse_value(), Token(BANG, "!"))
            return node

    def parse_expression(self) -> BinNode:
        '''
        An expression consists of:
        Expression: term PLUS | MINUS | EQTO | GTHAN | GETHAN | LTHAN | LETHAN | NEQTO term
        '''
        left = self.parse_term()

        while self.get_current_token().type in [PLUS, MINUS, EQTO, GTHAN, GETHAN, LTHAN, LETHAN, NEQTO]:
            action = self.get_current_token()
            self.advance()

            # Recursivly define the left node as the left node PLUS | MINUS the right node, and parse the right node
            # This way, in case of a long expression (ex: 4 + 3 + 2 + 1), the older nodes will be pushed left
            left = BinNode(left, action, self.parse_term())

        return left

    def parse_term(self) -> BinNode:
        '''
        A term consists of:
        Term: value MUL | DIV value || value
        '''
        left = self.parse_value()

        while self.get_current_token().type in [MUL, DIV]:
            action = self.get_current_token()
            self.advance()

            left = BinNode(left, action, self.parse_value())

        return left

    def parse_statement_list(self) -> StatementListNode:
        '''
        Parses a program. A program consists of statements, sepereated by semicolons
        '''

        compound = StatementListNode()
        statements = [self.parse_statement()]

        while self.get_current_token().type in [SEMI]:
            self.advance()

            if self.get_current_token().type != EOF:

                statements.append(self.parse_statement())

                #Remove Nones from the statement list
                if statements[-1] == None:
                    statements.pop()

        compound.statements.extend(statements)

        return compound

    def parse_statement(self):
        '''
        A statement consists of:
        Statement: assignment 
        '''
        if self.get_current_token().type == ID:

            #If its a function call
            if self.peek().type == LPAREN:
                return self.parse_functioncall()
            else:
                #Assignment
                var = self.get_current_token()
                self.advance()
                action = self.get_current_token()
                self.advance()

                if action.type in [ASSIGN, PLUSEQ, MINUSEQ]:
                    return AssignmentNode(var, action, self.parse_expression())
                elif action.type in [PLUSPLUS, MINUSMINUS]:
                    #Convert ++ and -- to either += 1 or -= 1
                    action = Token(PLUSEQ, "+=") if action.type == PLUSPLUS else Token(MINUSEQ, "-=")
                    return AssignmentNode(var, action, ValueNode(Token(INTEGER, 1)))

        elif self.get_current_token().type in Keywords:
            keyword = self.get_current_token()

            if keyword.type == "RETURN":
                self.advance()
                return_value = self.parse_value()
                return ActionNode(Token("RETURN", "RETURN"), return_value)

            elif keyword.type == "IF":
                self.advance()
                condition = self.parse_expression()
                self.consume(LCURL)
                if_statement_list = self.parse_statement_list()
                self.consume(RCURL)

                # Check for else
                if self.peek().type == "ELSE":
                    self.consume(SEMI)
                    self.consume("ELSE")
                    self.consume(LCURL)
                    else_statement_list = self.parse_statement_list()
                    self.consume(RCURL)

                    return IfNode(condition, if_statement_list, else_statement_list)
                else:
                    return IfNode(condition, if_statement_list, None)

            elif keyword.type == "FOR":
                self.advance()
                self.consume(LPAREN)
                init_statement = self.parse_for_init()
                self.consume(RPAREN)

                self.consume(LCURL)
                statement_list = self.parse_statement_list()
                self.consume(RCURL)
                return ForNode(init_statement, statement_list)

            elif keyword.type == "WHILE":
                self.advance()
                self.consume(LPAREN)
                condition = self.parse_expression()
                self.consume(RPAREN)

                self.consume(LCURL)
                statement_list = self.parse_statement_list()
                self.consume(RCURL)
                return WhileNode(condition, statement_list)

            elif keyword.type == "BREAK":
                self.advance()
                return ActionNode(Token("BREAK", "BREAK"), None)

            elif keyword.type == "PRINT":
                self.advance()
                val = self.parse_value()
                return ActionNode(Token("PRINT", "PRINT"), val)

            elif keyword.type == "FUNC":
                self.advance()
                funcname = self.consume(ID)

                #Consume parameters
                self.consume(LPAREN)
                
                paramlist = []
                # If there are parameters
                if self.get_current_token().type == ID:
                    paramlist.append(self.consume(ID))
                    while self.get_current_token().type == COMMA:
                        self.consume(COMMA)
                        paramlist.append(self.consume(ID))
                
                self.consume(RPAREN)
                self.consume(LCURL)
                statement_list = self.parse_statement_list()
                statement_list.isFunction = True
                self.consume(RCURL)
                return FunctionDefenitionNode(funcname, paramlist, statement_list)

        return None

    def parse_for_init(self):
        '''
        Defines the syntax for a for init statement, for example:
        (a : 1 to 10)
        '''
        variable = self.consume(ID)
        self.consume(COLON)
        startval = self.parse_value()
        self.consume("TO")
        endval = self.parse_value()
        return {"VAR": variable, "START": startval, "END": endval}

    def parse_functioncall(self):
        funcname = self.consume(ID)

        self.consume(LPAREN)
        
        arglist = []
        # If there are parameters
        if self.get_current_token().type != RPAREN:
            arglist.append(self.parse_value())
            while self.get_current_token().type == COMMA:
                self.consume(COMMA)
                arglist.append(self.parse_value())
        
        self.consume(RPAREN)
        return FunctionCallNode(funcname, arglist)

    def parse(self):
        return self.parse_statement_list()
