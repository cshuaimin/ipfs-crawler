CREATE EXTENSION pg_jieba;

CREATE TABLE html (
    hash varchar(49), 
    filename varchar(128),
    title text,
    text text,
    tsv tsvector
);
CREATE INDEX tsv_idx ON html USING GIN (tsv);

CREATE TABLE parsed (hash varchar(49));

CREATE FUNCTION tsv_update_trigger() RETURNS trigger AS $$
begin
  new.tsv :=
    setweight(to_tsvector('jiebaqry', coalesce(new.title, '')), 'A') ||
    setweight(to_tsvector('jiebaqry', coalesce(new.text, '')), 'C');
  return new;
end
$$ LANGUAGE plpgsql;

CREATE TRIGGER tsvupdate BEFORE INSERT OR UPDATE
ON html FOR EACH ROW EXECUTE PROCEDURE tsv_update_trigger();
