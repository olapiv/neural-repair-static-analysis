using System;
using System.Collections.Generic;
using System.Linq;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.Text;


namespace SourceCodeTokenizer
{
    public class TokenIndex
    {

        private IList<SyntaxToken> tokens;
        public Dictionary<TextSpan, (SyntaxToken SyntaxToken, int Position)> SpanToTokenIndex;

        public TokenIndex(IEnumerable<SyntaxToken> tokens)
        {
            this.tokens = new List<SyntaxToken>(tokens);
        }

        public IEnumerable<SyntaxToken> GetTokensInSpan(TextSpan querySpan)
        {
            var querySpanStart = querySpan.Start;
            var querySpanEnd = querySpan.End;

            return GetTokensInSpan(querySpanStart, querySpanEnd);
        }

        public TokenIndex WithVariableNameMap(IDictionary<string, string> variableNameMap)
        {
            var retainedTokens = tokens.Where(token => variableNameMap.ContainsKey(token.ValueText))
                .Select(token => SyntaxFactory.Token(token.LeadingTrivia, token.Kind(), token.Text, variableNameMap[token.ValueText], token.TrailingTrivia));

            return new TokenIndex(retainedTokens);
        }

        public TokenIndex InitInvertedIndex()
        {
            this.SpanToTokenIndex = new Dictionary<TextSpan, (SyntaxToken SyntaxToken, int Position)>();

            for (int i = 0; i < this.tokens.Count; i++)
            {
                var curToken = this.tokens[i];
                var key = curToken.Span;
                SpanToTokenIndex[key] = (curToken, i);
            }

            return this;
        }

        public IEnumerable<SyntaxToken> GetTokensInSpan(int start, int end)
        {
            var queryTokens = tokens.Where(token => token.SpanStart >= start).TakeWhile(token => token.Span.End <= end);

            return queryTokens;
        }

        public (SyntaxToken? SyntaxToken, int Position) GetTokenAndPositionBySpan(TextSpan span)
        {
            if (this.SpanToTokenIndex.ContainsKey(span))
            {
                return this.SpanToTokenIndex[span];
            }

            return (null, -1);
        }
    }
}
