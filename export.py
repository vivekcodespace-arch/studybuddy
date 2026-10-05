import genanki, random
import io
import csv


def export_to_anki(cards, deck_name, output_path):
    model = genanki.Model(
        1607392319,
        'Simple Model',
        fields=[{'name': 'Question'}, {'name': 'Answer'}],
        templates=[{
            'name': 'Card 1',
            'qfmt': '{{Question}}',
            'afmt': '{{FrontSide}}<hr id="answer">{{Answer}}',
        }])
    deck = genanki.Deck(random.randrange(1 << 30, 1 << 31), deck_name)
    for card in cards:
        deck.add_note(genanki.Note(model=model, fields=[card['q'], card['a']]))
    genanki.Package(deck).write_to_file(output_path)

def to_csv(cards):
    buf = io.StringIO()
    writer = csv.writer(buf)
    for card in cards:
        writer.writerow([card["q"], card["a"]])
    return buf.getvalue().encode("utf-8")