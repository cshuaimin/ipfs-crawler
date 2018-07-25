<template>
    <Layout>
        <Header class="header">
            <div class="vcenter">
                <router-link to="/" style="margin-right: 20px; height: 48px">
                    <img src="../assets/ipfs.svg" alt="IPFS" height="100%">
                </router-link>
                <Input
                    title="Search IPFS"
                    :autofocus="true"
                    icon="android-search"
                    placeholder="Search IPFS..."
                    @on-enter="search"
                    @on-click="search"
                    v-model="q"
                    size="large"
                    style="width: 598px"
                    >
                </Input>
            </div>
        </Header>
        <Content v-if="result" style="margin: 0 90px">
            <div class="result-item" v-for="item in result.hits" :key="item._id">
              <a slot="title" :href="`http://127.0.0.1:8080/ipfs/${item._id}`">
                    <div class="link">
                      <p class="title">{{ item._source.title || item._source.filename || item._source.content }}</p>
                      <p class="url">{{ item._id }}</p>
                    </div>
                </a>
                <p class="content" v-html="item.highlight.content"></p>
            </div>
        </Content>
    </Layout>
</template>

<style scoped>
.header {
    padding: 0 20px;
    background-color: white;
    border-bottom: 1px solid #ddd;
    box-shadow: 0 2px 10px #ddd;
}

.vcenter {
    height: 100%;
    display: flex;
    align-items: center;
}

.result-item {
    width: 60vw;
    margin: 26px 0;
}

.title {
    font-size: 18px;
    line-height: 1.2;
    color: #1967D2;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.url {
    font-size: 14px;
    color: #006621;
}

.content {
  font-size: small;
}
</style>

<style>
em {
  color: #dd4b39;
  font-style: normal;
}
</style>

<script>
import axios from 'axios'

export default {
  name: 'Results',
  props: ['query'],
  data () {
    return {
      q: this.query,
      result: null
    }
  },
  async mounted () {
    this.result = (await axios.get(`//127.0.0.1:8000/search/${this.q}`)).data
  },
  methods: {
    async search () {
      this.$router.push(`/search/${this.q}`)
    }
  }
}
</script>
